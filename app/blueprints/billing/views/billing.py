from flask import (
  Blueprint,
  current_app,
  render_template,
  url_for,
  request,
  redirect,
  flash,
)

from flask_login import login_required, current_user
from config import settings
from app.blueprints.billing.forms import CreditCardForm, \
    UpdateSubscriptionForm, CancelSubscriptionForm
from app.blueprints.user.create_mailgun_user import delete_inbox
from app.blueprints.billing.models.subscription import Subscription
from app.blueprints.billing.models.invoice import Invoice
from app.blueprints.billing.decorators import subscription_required, \
    handle_stripe_exceptions
from app.extensions import cache, timeout

billing = Blueprint('billing', __name__, template_folder='../templates',
                    url_prefix='/subscription')


@billing.route('/pricing')
@cache.cached(timeout=timeout)
def pricing():
    if current_user.is_authenticated and current_user.subscription:
        return redirect(url_for('billing.update'))

    form = UpdateSubscriptionForm()

    return render_template('billing/pricing.html', form=form,
                           plans=settings.STRIPE_PLANS)


@billing.route('/create', methods=['GET', 'POST'])
@handle_stripe_exceptions
@login_required
def create():

    if current_user.subscription:
        flash('You already have an active subscription.', 'info')
        return redirect(url_for('user.settings'))

    plan = request.args.get('plan')
    subscription_plan = Subscription.get_plan_by_id(plan)

    # Guard against an invalid or missing plan.
    if subscription_plan is None and request.method == 'GET':
        flash('Sorry, that plan did not exist.', 'error')
        return redirect(url_for('billing.pricing'))

    stripe_key = current_app.config.get('STRIPE_PUBLISHABLE_KEY')
    form = CreditCardForm(stripe_key=stripe_key, plan=plan)

    if form.validate_on_submit():
        subscription = Subscription()
        created = subscription.create(user=current_user,
                                      name=request.form.get('name'),
                                      plan=request.form.get('plan'),
                                      coupon=request.form.get('coupon_code'),
                                      token=request.form.get('stripe_token'))

        if created:
            if request.form.get('plan') is not None:
                plan = request.form.get('plan')

                # Set the mailbox and email limits accordingly
                current_user.mailbox_limit = 1 if plan == 'hobby' else 10 if plan == 'startup' else 40 if plan == 'professional' else 100 if plan == 'enterprise' else 0
                current_user.email_limit = 400 if plan == 'hobby' else 2000 if plan == 'startup' else 5000 if plan == 'professional' else 15000 if plan == 'enterprise' else 0
                current_user.save()

            flash('Your account has been upgraded!', 'success')
        else:
            flash('You must enable JavaScript for this request.', 'warning')

        return redirect(url_for('user.settings'))

    return render_template('billing/payment_method.html',
                           form=form, plan=subscription_plan)


@billing.route('/update', methods=['GET', 'POST'])
@handle_stripe_exceptions
@subscription_required
@login_required
def update():
    current_plan = current_user.subscription.plan
    active_plan = Subscription.get_plan_by_id(current_plan)
    new_plan = Subscription.get_new_plan(request.form.keys())

    plan = Subscription.get_plan_by_id(new_plan)

    # Guard against an invalid, missing or identical plan.
    is_same_plan = new_plan == active_plan['id']
    if ((new_plan is not None and plan is None) or is_same_plan) and \
            request.method == 'POST':
        return redirect(url_for('billing.update'))

    form = UpdateSubscriptionForm(coupon_code=current_user.subscription.coupon)

    if form.validate_on_submit():
        subscription = Subscription()
        updated = subscription.update(user=current_user,
                                      coupon=request.form.get('coupon_code'),
                                      plan=plan.get('id'))

        if updated:
            if new_plan is not None:

                # Set the user's current mailbox to the oldest mailbox
                from app.blueprints.parse.models.mailbox import Mailbox
                mailbox = Mailbox.query.filter(Mailbox.user_email == current_user.email).order_by(Mailbox.created_on.asc()).first()

                if mailbox:
                    current_user.mailbox_id = mailbox.mailbox_id

                # Set the mailbox and email limits accordingly
                mailbox_limit = 10 if new_plan == 'hobby' else 40 if new_plan == 'startup'\
                    else 60 if new_plan == 'professional' else 100 if new_plan == 'enterprise'\
                    else 100 if new_plan == 'developer' else 0
                email_limit = 400 if new_plan == 'hobby' else 2000 if new_plan == 'startup'\
                    else 5000 if new_plan == 'professional' else 15000 if new_plan == 'enterprise'\
                    else 20000 if new_plan == 'developer' else 0

                # Adjust the mailboxes by deleting
                # the most recent mailboxes and emails
                from app.blueprints.user.tasks import adjust_mailboxes
                if plan['amount'] < active_plan['amount']:
                    current_user.email_count, current_user.mailbox_count = adjust_mailboxes(current_user.email,
                                                                                            current_user.mailbox_id,
                                                                                            current_user.email_count,
                                                                                            mailbox_limit,
                                                                                            email_limit)

                current_user.mailbox_limit, current_user.email_limit = mailbox_limit, email_limit
                current_user.save()

            flash('Your plan has been updated. Changes will take effect immediately.', 'success')
            return redirect(url_for('user.settings'))

    return render_template('billing/pricing.html',
                           form=form,
                           plans=settings.STRIPE_PLANS,
                           active_plan=active_plan)


@billing.route('/cancel', methods=['GET', 'POST'])
@handle_stripe_exceptions
@login_required
def cancel():

    form = CancelSubscriptionForm()

    if form.validate_on_submit():

        # Cancel the user's subscription
        if current_user.subscription:
            subscription = Subscription()
            canceled = subscription.cancel(user=current_user)
        else:
            # If there is no subscription, then delete the user
            canceled = True

        if canceled:

            # Get the user's email
            email = current_user.email

            # Clear the cache.
            mailbox_id = current_user.mailbox_id
            if cache.get(mailbox_id):
                cache.delete(mailbox_id)

            from app.blueprints.parse.models.mailbox import Mailbox

            # Delete the credentials from MG
            for mailbox in Mailbox.query.filter_by(user_email=email).all():
                delete_inbox(mailbox.mailbox_id)

            # Delete all emails, rules and mailboxes belonging to the user.
            from app.blueprints.user.tasks import delete_all
            delete_all.delay(email, mailbox_id)

            # Delete the user.
            from app.blueprints.billing.tasks import delete_users
            ids = [current_user.id]
            delete_users(ids)

            # Send a cancellation email.
            from app.blueprints.user.tasks import send_cancel_email
            send_cancel_email.delay(email)

            flash('Sorry to see you go! Your subscription has been canceled.',
                  'success')
            return redirect(url_for('user.login'))

    return render_template('billing/cancel.html', form=form)


@billing.route('/update_payment_method', methods=['GET', 'POST'])
@handle_stripe_exceptions
@login_required
def update_payment_method():
    if not current_user.credit_card:
        flash('You do not have a payment method on file.', 'error')
        return redirect(url_for('user.settings'))

    active_plan = Subscription.get_plan_by_id(
        current_user.subscription.plan)

    card = current_user.credit_card
    stripe_key = current_app.config.get('STRIPE_PUBLISHABLE_KEY')
    form = CreditCardForm(stripe_key=stripe_key,
                          plan=active_plan,
                          name=current_user.name)

    if form.validate_on_submit():
        subscription = Subscription()
        updated = subscription.update_payment_method(user=current_user,
                                                     credit_card=card,
                                                     name=request.form.get(
                                                         'name'),
                                                     token=request.form.get(
                                                         'stripe_token'))

        if updated:
            flash('Your payment method has been updated.', 'success')
        else:
            flash('You must enable JavaScript for this request.', 'warning')

        return redirect(url_for('user.settings'))

    return render_template('billing/payment_method.html', form=form,
                           plan=active_plan, card_last4=str(card.last4))


@billing.route('/billing_details')
@handle_stripe_exceptions
@login_required
def billing_details():
    invoices = Invoice.billing_history(current_user)

    if current_user.subscription:
        upcoming = Invoice.upcoming(current_user.payment_id)
        coupon = None
        # coupon = Coupon.query \
        #     .filter(Coupon.code == current_user.subscription.coupon).first()
    else:
        upcoming = None
        coupon = None

    return render_template('billing/billing_details.html',
                           invoices=invoices, upcoming=upcoming, coupon=coupon)
