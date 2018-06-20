import time
import redis
from flask import current_app
from lib.flask_mailplus import send_template_message
from app.extensions import cache, db
from app.app import create_celery_app
from app.blueprints.user.models import User
from app.blueprints.parse.models.email import Email
from app.blueprints.parse.models.rule import Rule


celery = create_celery_app()
# r = redis.StrictRedis(host=current_app.config.get('CACHE_REDIS_HOST'),password=current_app.config.get('CACHE_REDIS_PASSWORD'), port=13524, db=0)


@celery.task()
def deliver_password_reset_email(user_id, reset_token):
    """
    Send a reset password e-mail to a user.

    :param user_id: The user id
    :type user_id: int
    :param reset_token: The reset token
    :type reset_token: str
    :return: None if a user was not found
    """
    user = User.query.get(user_id)

    if user is None:
        return

    ctx = {'user': user, 'reset_token': reset_token}

    send_template_message(subject='Password reset from Parser',
                          recipients=[user.email],
                          template='user/mail/password_reset', ctx=ctx)

    return None


# Emails -------------------------------------------------------------------
@celery.task()
def get_emails(mailbox_id):
    emails = []

    for email in Email.query.with_entities(Email.id,Email.sender,Email.subject,Email.date,Email.parsed)\
            .filter(Email.mailbox_id == mailbox_id).all():
        emails.append({'id':email.id,'sender':email.sender,'subject':email.subject,
                       'date':email.date,'body':'','parsed':email.parsed})

    return emails


@celery.task()
def delete_emails(email):
    Email.query.filter(Email.id == email).delete()


# Rules -------------------------------------------------------------------
@celery.task()
def get_rules(mailbox_id):
    rules = []
    for rule in Rule.query.filter(Rule.mailbox_id == mailbox_id).all():
        rules.append({'id':rule.id,'name':rule.name,'section':rule.section,'category':rule.category,'options':rule.options,'args':rule.args})

    return rules


@celery.task()
def add_rule(section, category, options, name, args, mailbox_id):

    from app.blueprints.parse.models.rule import Rule

    r = Rule()
    r.mailbox_id = mailbox_id
    r.section = section
    r.category = category
    r.options = options
    r.name = name
    r.args = args

    db.session.add(r)
    db.session.commit()


@celery.task()
def delete_rules(to_delete):
    from app.blueprints.parse.models.rule import Rule

    for item in to_delete:
        Rule.query.filter(Rule.id == item).delete()

    db.session.commit()


# Cache -------------------------------------------------------------------
@celery.task()
def set_cache(mailbox_id, emails_id):

    emails = get_emails.AsyncResult(emails_id)

    if emails.state != 'PENDING':
        cache.set(mailbox_id, emails.result)
        # r.set(mailbox_id, emails.result)
    else:
        time.sleep(1)
        set_cache(mailbox_id, emails_id)
