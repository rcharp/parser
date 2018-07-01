from flask import (
    Blueprint,
    redirect,
    request,
    flash,
    url_for,
    render_template,
    json,
    jsonify)
from flask_login import (
    login_required,
    login_user,
    current_user,
    logout_user)

from lib.safe_next_url import safe_next_url
from app.blueprints.parse.parse import generate_csv
from app.blueprints.user.decorators import anonymous_required
from app.blueprints.user.models import User
from app.blueprints.user.create_mailgun_user import generate_mailbox_id, create_inbox
from app.blueprints.user.forms import (
    LoginForm,
    BeginPasswordResetForm,
    PasswordResetForm,
    SignupForm,
    WelcomeForm,
    UpdateCredentials)

import stripe
import datetime
from app.extensions import cache, csrf, timeout, db

user = Blueprint('user', __name__, template_folder='templates')


# Login and Credentials -------------------------------------------------------------------
@user.route('/login', methods=['GET', 'POST'])
@anonymous_required()
@cache.cached(timeout=timeout)
@csrf.exempt
def login():

    form = LoginForm(next=request.args.get('next'))

    if form.validate_on_submit():
        u = User.find_by_identity(request.form.get('identity'))

        if u and u.authenticated(password=request.form.get('password')):
            # As you can see remember me is always enabled, this was a design
            # decision I made because more often than not users want this
            # enabled. This allows for a less complicated login form.
            #
            # If however you want them to be able to select whether or not they
            # should remain logged in then perform the following 3 steps:
            # 1) Replace 'True' below with: request.form.get('remember', False)
            # 2) Uncomment the 'remember' field in user/forms.py#LoginForm
            # 3) Add a checkbox to the login form with the id/name 'remember'
            if login_user(u, remember=True) and u.is_active():
                u.update_activity_tracking(request.remote_addr)

                # Handle optionally redirecting to the next URL safely.
                next_url = request.form.get('next')
                if next_url:
                    return redirect(safe_next_url(next_url))

                if current_user.role == 'admin':
                    return redirect(url_for('admin.dashboard'))

                if current_user.role == 'member':

                    if not cache.get(current_user.mailbox_id):
                        from app.blueprints.user.tasks import get_emails, get_rules, set_cache

                        emails = get_emails.delay(current_user.mailbox_id)

                        set_cache.delay(current_user.mailbox_id, emails.id)

                    if current_user.trial:
                        trial_days_left = 14 - (datetime.datetime.now() - current_user.created_on.replace(tzinfo=None)).days
                        if trial_days_left < 0:
                            current_user.trial = False
                            current_user.save()

                return redirect(url_for('user.settings'))
            else:
                flash('This account has been disabled.', 'error')
        else:
            flash('Your username/email or password is incorrect.', 'error')

    return render_template('user/login.html', form=form)


@user.route('/logout')
@login_required
@cache.cached(timeout=timeout)
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('user.login'))


@user.route('/account/begin_password_reset', methods=['GET', 'POST'])
@anonymous_required()
def begin_password_reset():
    form = BeginPasswordResetForm()

    if form.validate_on_submit():
        u = User.initialize_password_reset(request.form.get('identity'))

        flash('An email has been sent to {0}.'.format(u.email), 'success')
        return redirect(url_for('user.login'))

    return render_template('user/begin_password_reset.html', form=form)


@user.route('/account/password_reset', methods=['GET', 'POST'])
@anonymous_required()
def password_reset():
    form = PasswordResetForm(reset_token=request.args.get('reset_token'))

    if form.validate_on_submit():
        u = User.deserialize_token(request.form.get('reset_token'))

        if u is None:
            flash('Your reset token has expired or was tampered with.',
                  'error')
            return redirect(url_for('user.begin_password_reset'))

        form.populate_obj(u)
        u.password = User.encrypt_password(request.form.get('password'))
        u.save()

        if login_user(u):
            flash('Your password has been reset.', 'success')
            return redirect(url_for('user.settings'))

    return render_template('user/password_reset.html', form=form)


@user.route('/signup', methods=['GET', 'POST'])
@anonymous_required()
@cache.cached(timeout=timeout)
def signup():
    form = SignupForm()

    if form.validate_on_submit():
        u = User()

        form.populate_obj(u)
        u.password = User.encrypt_password(request.form.get('password'))
        u.save()

        if login_user(u):

            from app.blueprints.user.tasks import send_welcome_email
            send_welcome_email.delay(current_user.email)

            # Create a user id for the user
            mailbox_id = generate_mailbox_id()

            # Create an inbox for the user
            if create_inbox(mailbox_id):
                current_user.mailbox_count += 1
                current_user.active_mailbox = True
                current_user.mailbox_id = mailbox_id

                current_user.save()

                from app.blueprints.parse.models.mailbox import Mailbox

                m = Mailbox()
                m.mailbox_id = mailbox_id
                m.user_email = current_user.email
                db.session.add(m)

                from app.blueprints.parse.models.rule import Rule

                # Create default rules
                rules = ['Sender', 'To', 'Subject', 'Date']

                for rule in rules:
                    r = Rule()
                    r.mailbox_id = mailbox_id
                    r.rule = rule

                    # Add the default rules to the database
                    db.session.add(r)

                db.session.commit()
                flash('Awesome, thanks for signing up!', 'success')
            else:
                flash('There was a problem creating an inbox for you. Please try again.', 'error')
                current_user.active_mailbox = False
                current_user.mailbox_count = 0
                current_user.mailbox_id = None

                current_user.save()

            return redirect(url_for('user.settings'))

    return render_template('user/signup.html', form=form)


@user.route('/welcome', methods=['GET', 'POST'])
@login_required
def welcome():
    if current_user.username:
        flash('You already picked a username.', 'warning')
        return redirect(url_for('user.settings'))

    form = WelcomeForm()

    if form.validate_on_submit():
        current_user.username = request.form.get('username')
        current_user.save()

        flash('Your username has been set.', 'success')
        return redirect(url_for('user.settings'))

    return render_template('user/welcome.html', form=form, payment=current_user.payment_id)


@user.route('/settings/update_credentials', methods=['GET', 'POST'])
@login_required
def update_credentials():
    form = UpdateCredentials(current_user, uid=current_user.id)

    if form.validate_on_submit():
        new_password = request.form.get('password', '')
        current_user.email = request.form.get('email')

        if new_password:
            current_user.password = User.encrypt_password(new_password)

        current_user.save()

        flash('Your sign in settings have been updated.', 'success')
        return redirect(url_for('user.settings'))

    return render_template('user/update_credentials.html', form=form)


# Emails -------------------------------------------------------------------
@user.route('/delete_emails', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def delete_emails():
    if request.method == "POST":

        to_delete = request.form.getlist('delete')

        from app.blueprints.user.tasks import delete_emails
        for item in to_delete:
            delete_emails(item)

        db.session.commit()

    flash('Email(s) successfully deleted.', 'error')
    return redirect(url_for('user.refresh'))


@user.route('/parse/<email_id>', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def parse(email_id):

    if request.method == 'GET':
        if current_user.subscription or current_user.trial:
            if current_user.mailbox_id:

                from app.blueprints.user.tasks import get_rules

                rules = get_rules(current_user.mailbox_id)

                from app.blueprints.parse.models.email import Email
                email = Email.query.filter(Email.id == email_id).first()

                body = Email.query.with_entities(Email.body).filter(Email.id == email_id).first()

                return render_template('user/parse.html', rules=rules, email=email, body=body, mailbox_id=current_user.mailbox_id, email_id=email_id)
            else:
                flash('You don\'t have an inbox yet. Please create one below.', 'error')
        return redirect(url_for('user.settings'))


@user.route('/parse_email/<email_id>', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def parse_email(email_id):

    rules = request.form.getlist('select')
    autoparse = request.form.get('autoparse')

    if autoparse == "true":
        autoparse = 1
    else:
        autoparse = 0

    from app.blueprints.parse.parse import parse_email
    parse_email(email_id,rules,autoparse)

    flash('Your email has been parsed. Check it out below!', 'success')
    return redirect(url_for('user.refresh'))


@user.route('/view_email/<email_id>', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def view_email(email_id):
    from app.blueprints.parse.models.email import Email
    email = Email.query.filter(Email.id == email_id).first()
    return render_template('user/view.html', mailbox_id=current_user.mailbox_id, email=email)


# Rules -------------------------------------------------------------------
@user.route('/rules', methods=['GET', 'POST'])
@login_required
def rules():
    stripe.api_version = '2018-02-28'

    if request.method == 'GET':
        if current_user.subscription or current_user.trial:
            if current_user.mailbox_id:

                from app.blueprints.user.tasks import get_rules

                rules = get_rules(current_user.mailbox_id)
                return render_template('user/rules.html', mailbox_id=current_user.mailbox_id, rules=rules)
            else:
                flash('You don\'t have an inbox yet. Please create one below.', 'error')
        return redirect(url_for('user.settings'))


@user.route('/add_rule/<email_id>', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def add_rule(email_id):
    if request.method == 'POST':

        # Get the new rules
        sections = request.form.getlist('checkbox')

        if '' in sections:
            sections = list(filter(None, sections))

        section = sections[0]
        category = request.form.get('category')
        options = request.form.get(category + '_options')
        name = request.form['name']
        args = request.form['args']

        from app.blueprints.user.tasks import add_rule
        add_rule(section, category, options, name, args, current_user.mailbox_id)

        flash('Rule has been successfully added.', 'success')
        if email_id == "0":
            return redirect(url_for('user.rules'))
        else:
            return redirect(url_for('user.parse',email_id=email_id))


@user.route('/add/<email_id>', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def add(email_id):
    return render_template('user/add.html', email_id=email_id, mailbox_id=current_user.mailbox_id)


@user.route('/delete_rules', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def delete_rules():
    if request.method == "POST":

        to_delete = request.form.getlist('delete')

        from app.blueprints.user.tasks import delete_rules

        delete_rules(to_delete)

    flash('Rule(s) successfully deleted.', 'error')
    return redirect(url_for('user.rules'))


# Settings -------------------------------------------------------------------
@user.route('/settings', methods=['GET','POST'])
@login_required
@csrf.exempt
def settings():
    cache.clear()
    mailbox_id = current_user.mailbox_id
    trial_days_left = -1

    from app.blueprints.user.tasks import get_mailboxes

    mailbox_count, mailbox_limit = current_user.mailbox_count, current_user.mailbox_limit
    email_count, email_limit = current_user.email_count, current_user.email_limit
    mailboxes = get_mailboxes(current_user.email)

    if not current_user.subscription and not current_user.trial and current_user.role == 'member':
        flash('Your free trial has expired. Please sign up for a plan below to continue parsing emails.',
              'error')

    if current_user.trial and current_user.role == 'member':
        trial_days_left = 14 - (datetime.datetime.now() - current_user.created_on.replace(tzinfo=None)).days

    if not current_user.active_mailbox:
        flash('You don\'t have an inbox yet. Please create one below.', 'error')

    return render_template('user/settings.html', trial_days_left=trial_days_left, mailbox_id=mailbox_id,
                           mailbox_count=mailbox_count, mailbox_limit=mailbox_limit,
                           email_count=email_count, email_limit=email_limit, mailboxes=mailboxes)


# Inbox -------------------------------------------------------------------
@user.route('/inbox', methods=['GET', 'POST'])
@login_required
def inbox():
    if request.method == 'GET':
        if current_user.subscription or current_user.trial:
            if current_user.active_mailbox:
                if cache.get(current_user.mailbox_id):
                    emails = cache.get(current_user.mailbox_id)
                    return render_template('user/inbox.html', emails=emails, mailbox_id=current_user.mailbox_id, route="inbox")
                else:
                    return redirect(url_for('user.refresh'))
            else:
                flash('You don\'t have an inbox yet. Please create one below.', 'error')
        return redirect(url_for('user.settings'))


@user.route('/refresh', methods=['GET', 'POST'])
@login_required
def refresh():
        from app.blueprints.user.tasks import get_emails, set_cache

        emails = get_emails.delay(current_user.mailbox_id)
        set_cache.delay(current_user.mailbox_id, emails.id)

        return render_template('user/inbox.html', emails_id=emails.id, emails_state=emails.state,
                               mailbox_id=current_user.mailbox_id, emails=[], route="refresh")


@user.route('/update/<emails_id>/<route>')
@csrf.exempt
def update(emails_id,route):

    if route == "dashboard":
        return jsonify({'route': 'dashboard'})
    elif route == "refresh":
        from app.blueprints.user.tasks import get_emails
        emails = get_emails.AsyncResult(emails_id)

        return jsonify({'route':'refresh', 'emails_result': emails.result, 'emails_state':emails.state})


# Utilities -------------------------------------------------------------------
@user.route('/export', methods=['GET', 'POST'])
@login_required
def export():
    from app.blueprints.user.tasks import export_emails

    emails = export_emails(current_user.mailbox_id)
    file = generate_csv(emails)

    from app.blueprints.user.tasks import send_export_email
    send_export_email.delay(current_user.email, file)

    flash('Your CSV has been sent to your email.', 'success')
    return redirect(url_for('user.inbox'))


@user.route('/get_inbox', methods=['GET', 'POST'])
@login_required
def get_inbox():

    count, limit = current_user.mailbox_count, current_user.mailbox_limit
    if count < limit:

        # Create a user id for the user
        mailbox_id = generate_mailbox_id()
        current_user.mailbox_id = mailbox_id

        # Create an inbox for the user
        if create_inbox(mailbox_id):
            current_user.active_mailbox = True
            current_user.mailbox_count += 1

            from app.blueprints.parse.models.mailbox import Mailbox

            m = Mailbox()
            m.mailbox_id = mailbox_id
            m.user_email = current_user.email

            db.session.add(m)
            db.session.commit()

            flash('Your inbox has been created.', 'success')
        else:
            flash('There was a problem creating an inbox for you. Please try again.', 'error')
            current_user.active_mailbox = False
            current_user.mailbox_id = None

        current_user.save()
    else:
        flash('You\'ve reached your limit for mailboxes. Please upgrade to get more.', 'error')

    return redirect(url_for('user.settings'))


@user.route('/switch_mailboxes', methods=['GET', 'POST'])
@csrf.exempt
def switch_mailboxes():

    mailbox_id = request.form.get('mailboxes')

    current_user.mailbox_id = mailbox_id
    current_user.save()

    return redirect(url_for('user.refresh'))


# Webhooks -------------------------------------------------------------------
@user.route('/webhooks', methods=['GET','POST'])
@csrf.exempt
def webhooks():
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
