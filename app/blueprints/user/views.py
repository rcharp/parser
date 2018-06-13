from flask import (
    Blueprint,
    redirect,
    request,
    flash,
    url_for,
    render_template,
    current_app,
    json,
    jsonify)
from flask_login import (
    login_required,
    login_user,
    current_user,
    logout_user)

from lib.safe_next_url import safe_next_url
from app.blueprints.user.decorators import anonymous_required
import app.blueprints.simple.prettydate as p
from app.blueprints.simple.date import get_datetime_from_string
from app.blueprints.user.models import User
from app.blueprints.user.templates.emails import send_welcome_email
from app.blueprints.user.forms import (
    LoginForm,
    BeginPasswordResetForm,
    PasswordResetForm,
    SignupForm,
    WelcomeForm,
    UpdateCredentials)

import datetime
import requests
import stripe
from app.extensions import cache, csrf, timeout

user = Blueprint('user', __name__, template_folder='templates')


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

            send_welcome_email(current_user.email)
            # flash('Awesome, thanks for signing up! Please choose a plan that best fits your needs.', 'success')
            # return redirect(url_for('billing.pricing'))
            flash('Awesome, thanks for signing up! Please connect your Stripe account below.', 'success')
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


@user.route('/webhooks', methods=['GET','POST'])
@csrf.exempt
def webhooks():
<<<<<<< HEAD

=======
>>>>>>> 3d297c14e990a09a847e151bfb36e5a31283e34a
    data = request.form
    for k in data:
        print(k + ": " + data[k] + "\n")

    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


@user.route('/settings', methods=['GET','POST'])
@login_required
@csrf.exempt
def settings():
    stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')
    stripe.api_version = '2018-02-28'
    stripe_link = current_app.config.get('STRIPE_AUTHORIZATION_LINK')
    trial_days_left = -1

    if not current_user.subscription and not current_user.trial and current_user.role == 'member':
        flash('Your free trial has expired. Please sign up for a plan below to continue getting your Stripe metrics.',
              'error')

    if current_user.trial and current_user.role == 'member':
        trial_days_left = 14 - (datetime.datetime.now() - current_user.created_on.replace(tzinfo=None)).days
        # flash('You have ' + str(trial_days_left) + ' day(s) left on your free trial.', 'error')

    if current_user.stripe_id is None:
        if request.args.get("code"):
            url = "https://connect.stripe.com/oauth/token"

            r = requests.post(url, json={"client_secret": current_app.config['STRIPE_SECRET_KEY'],
                                         "code": request.args.get("code"), "grant_type":
                                             "authorization_code"})

            if "refresh_token" in r.json():
                current_user.refresh_token = str(r.json()['refresh_token'])

            if "error" in r.json():
                if str(r.json()['error'] == 'invalid_grant'):
                    r = requests.post(url, json={"client_secret": current_app.config['STRIPE_SECRET_KEY'],
                                                 "code": current_user.refresh_token, "grant_type":
                                                     "refresh_token"})

            current_user.stripe_id = str(r.json()['stripe_user_id'])
            current_user.save()

            if not cache.get(current_user.email):
                from app.blueprints.user.tasks import get_events_list, get_all_metrics, set_cache

                updated = datetime.datetime.now()
                events = get_events_list.delay(current_user.stripe_id)
                metrics = get_all_metrics.delay(current_user.stripe_id)

                set_cache.delay(current_user.email, events.id, metrics.id, updated)

            email = stripe.Account.retrieve(current_user.stripe_id).email

            flash("You've successfully conntected your Stripe account. You can choose a username below or head to the dashboard now!", 'success')
            return render_template('user/settings.html', email=email, stripe_link=stripe_link, trial_days_left=trial_days_left)
        elif request.args.get('error') == 'access_denied':
            flash('Your have to connect your Stripe account. Please try again.', 'error')
        return render_template('user/settings.html', stripe_link=stripe_link, trial_days_left=trial_days_left)
    else:
        email = stripe.Account.retrieve(current_user.stripe_id).email
        return render_template('user/settings.html', email=email, stripe_link=stripe_link, trial_days_left=trial_days_left)


# Dashboard -------------------------------------------------------------------
@user.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    stripe.api_version = '2018-02-28'

    if request.method == 'GET':
        if current_user.subscription or current_user.trial:
            if current_user.stripe_id:

                # Cache the results.
                if cache.get(current_user.email):
                    events, metrics, updated = cache.get(current_user.email)
                else:
                    return redirect(url_for('user.refresh'))
                    # from app.blueprints.user.tasks import get_events_list, get_all_metrics, set_cache
                    #
                    # metrics = get_all_metrics.delay(current_user.stripe_id)
                    # events = get_events_list.delay(current_user.stripe_id)
                    #
                    # updated = datetime.datetime.now()
                    # name = current_user.username
                    #
                    # set_cache.delay(current_user.email, events.id, metrics.id, updated)
                    #
                    # return render_template('user/dashboard.html', metrics_id=metrics.id, metrics_state=metrics.state,
                    #                        events_id=events.id, events_state=events.state,
                    #                        route="dashboard", name=name, updated="Just now")

                # Get all of the metrics.
                mrr, customers, new_customers, refunds, net_rev, failed, cancellations,\
                churn, arpu, arr, ltv = metrics['MRR'], metrics['Customers'], metrics['New_Customers'], \
                                        metrics['Refunds'], metrics['Net_Revenue'], metrics['Failed'], \
                                        metrics['Canceled'], metrics['Churn'], metrics['ARPU'],  metrics['ARR'], \
                                        metrics['LTV']

                # Calculate percentages
                percentages = percent(metrics)
                for k,v in percentages.items():
                    percentages[k] = convert_to_percent(v)

                mrr_pct, customers_pct, new_customers_pct, refunds_pct, net_revenue_pct, failed_pct, \
                canceled_pct, arpu_pct, arr_pct = percentages['MRR_Pct'],percentages['Customers_Pct'], \
                                                                  percentages['New_Customers_Pct'], percentages['Refunds_Pct'],\
                                                                  percentages['Net_Revenue_Pct'], percentages['Failed_Pct'], \
                                                                  percentages['Canceled_Pct'], percentages['ARPU_Pct'], \
                                                                  percentages['ARR_Pct']

                name = current_user.username
                last_updated = p.date(datetime.datetime.now() - get_datetime_from_string(updated))

                return render_template('user/dashboard.html', events=events,events_id=0,
                                       metrics=metrics,metrics_id=0,
                                       route="dashboard", name=name, updated=last_updated,
                                       mrr=mrr, mrr_pct=mrr_pct,
                                       active_customers=customers, customers_pct=customers_pct,
                                       net_revenue=net_rev, net_revenue_pct=net_revenue_pct,
                                       failed=failed, failed_pct=failed_pct,
                                       #upgrades=upgrades, upgrades_pct=upgrades_pct,
                                       #downgrades=downgrades, downgrades_pct=downgrades_pct,
                                       new_customers=new_customers, new_customers_pct=new_customers_pct,
                                       cancellations=cancellations, canceled_pct=canceled_pct,
                                       refunds=refunds, refunds_pct=refunds_pct,
                                       arpu=arpu,arpu_pct=arpu_pct,
                                       arr=arr,arr_pct=arr_pct,
                                       churn=churn,
                                       ltv=ltv)
            else:
                flash('You have to connect your Stripe account to access the dashboard. Please connect below.', 'error')
                return redirect(url_for('user.settings'))
        else:
            #flash('Your free trial has expired. Please sign up for a plan below to continue getting your Stripe metrics.', 'error')
            return redirect(url_for('user.settings'))

# </editor-fold>
