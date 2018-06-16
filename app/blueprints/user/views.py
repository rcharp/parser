from flask import (
    Blueprint,
    redirect,
    request,
    flash,
    url_for,
    render_template,
    current_app,
    json)
from flask_login import (
    login_required,
    login_user,
    current_user,
    logout_user)

from lib.safe_next_url import safe_next_url
from app.blueprints.user.decorators import anonymous_required
from app.blueprints.user.models import User
from app.blueprints.user.create_mailgun_user import generate_mailbox_id, create_inbox
from app.blueprints.parse.parse import get_emails, get_rules
from app.blueprints.user.templates.emails import send_welcome_email
from app.blueprints.user.forms import (
    LoginForm,
    BeginPasswordResetForm,
    PasswordResetForm,
    SignupForm,
    WelcomeForm,
    UpdateCredentials)

import datetime
import stripe
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

            # send_welcome_email(current_user.email).delay()

            # Create a user id for the user
            mailbox_id = generate_mailbox_id()
            current_user.mailbox_id = mailbox_id

            # Create an inbox for the user
            if create_inbox(mailbox_id):
                current_user.active_mailbox = True

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

    return render_template('user/welcome.html', form=form)


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
@user.route('/get_inbox', methods=['GET', 'POST'])
@login_required
def get_inbox():

    # Create a user id for the user
    mailbox_id = generate_mailbox_id()
    current_user.mailbox_id = mailbox_id

    # Create an inbox for the user
    if create_inbox(mailbox_id):
        current_user.active_mailbox = True
        flash('Your inbox has been created.', 'success')
    else:
        flash('There was a problem creating an inbox for you. Please try again.', 'error')
        current_user.active_mailbox = False

    current_user.save()

    flash('Your sign in settings have been updated.', 'success')
    return redirect(url_for('user.settings'))


@user.route('/delete_emails', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def delete_emails():
    if request.method == "POST":

        to_delete = request.form.getlist('delete')

        from app.blueprints.parse.models.email import Email

        for item in to_delete:
            Email.query.filter(Email.id == item).delete()

        db.session.commit()

    flash('Email(s) successfully deleted.', 'error')
    return redirect(url_for('user.inbox'))


# Rules -------------------------------------------------------------------
@user.route('/rules', methods=['GET', 'POST'])
@login_required
def rules():
    stripe.api_version = '2018-02-28'

    if request.method == 'GET':
        if current_user.subscription or current_user.trial:
            if current_user.mailbox_id:
                rules = get_rules(current_user.mailbox_id)
                return render_template('user/rules.html', rules=rules)
            else:
                flash('You don\'t have an inbox yet. Please get one below.', 'error')
        return redirect(url_for('user.settings'))


@user.route('/add_rule/', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def add_rule():
    if request.method == 'POST':
        # Get the new rules
        new_rules = request.form.getlist('new_rule')

        if '' in new_rules:
            rules = list(filter(None, new_rules))
        else:
            rules = new_rules

        from app.blueprints.parse.models.rule import Rule

        for rule in rules:
            r = Rule()
            r.mailbox_id = current_user.mailbox_id
            r.rule = rule

            db.session.add(r)
        db.session.commit()

    flash('Rules have been successfully added.', 'success')
    return redirect(url_for('user.rules'))


@user.route('/edit_rules', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def edit_rules():
    if request.method == "POST":
        if request.form['action'] == 'delete':
            to_delete = request.form.getlist('delete')

            from app.blueprints.parse.models.rule import Rule

            for item in to_delete:
                Rule.query.filter(Rule.id == item).delete()

            db.session.commit()
            flash('Rule(s) successfully deleted.', 'error')

        elif request.form['action'] == 'save':
            new_rules = request.form.getlist('new_rule')

            if '' in new_rules:
                rules = list(filter(None, new_rules))
            else:
                rules = new_rules

            from app.blueprints.parse.models.rule import Rule

            for rule in rules:
                r = Rule()
                r.mailbox_id = current_user.mailbox_id
                r.rule = rule

                db.session.add(r)
            db.session.commit()
            flash('Rules have been successfully added.', 'success')

    return redirect(url_for('user.rules'))


@user.route('/delete_rules', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def delete_rules():
    if request.method == "POST":

        to_delete = request.form.getlist('delete')

        from app.blueprints.parse.models.rule import Rule

        for item in to_delete:
            Rule.query.filter(Rule.id == item).delete()

        db.session.commit()

    flash('Rule(s) successfully deleted.', 'error')
    return redirect(url_for('user.rules'))


# Settings -------------------------------------------------------------------
@user.route('/settings', methods=['GET','POST'])
@login_required
@csrf.exempt
def settings():
    stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')
    stripe.api_version = '2018-02-28'
    mailbox_id = current_user.mailbox_id
    trial_days_left = -1

    if not current_user.subscription and not current_user.trial and current_user.role == 'member':
        flash('Your free trial has expired. Please sign up for a plan below to continue parsing emails.',
              'error')

    if current_user.trial and current_user.role == 'member':
        trial_days_left = 14 - (datetime.datetime.now() - current_user.created_on.replace(tzinfo=None)).days

    return render_template('user/settings.html', trial_days_left=trial_days_left, mailbox_id=mailbox_id)


# Inbox -------------------------------------------------------------------
@user.route('/inbox', methods=['GET', 'POST'])
@login_required
def inbox():
    stripe.api_version = '2018-02-28'

    if request.method == 'GET':
        if current_user.subscription or current_user.trial:
            if current_user.mailbox_id:
                emails = get_emails(current_user.mailbox_id)
                return render_template('user/inbox.html', emails=emails)
            else:
                flash('You don\'t have an inbox yet. Please get one below.', 'error')
        return redirect(url_for('user.settings'))


# Webhooks -------------------------------------------------------------------
@user.route('/webhooks', methods=['GET','POST'])
@csrf.exempt
def webhooks():
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
