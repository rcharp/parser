import time
import asyncio
from operator import itemgetter
from itertools import groupby
from heapq import merge
from aiopg.sa import create_engine
from flask import current_app
import sqlalchemy as sa
from lib.flask_mailplus import send_template_message
from app.extensions import cache, db
from app.app import create_celery_app
from app.blueprints.user.models import User


celery = create_celery_app()


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

    send_template_message(subject='Password reset from Parsavvy',
                          recipients=[user.email],
                          template='user/mail/password_reset', ctx=ctx)

    return None


# Mailboxes -------------------------------------------------------------------
@celery.task()
def adjust_mailboxes(email, mailbox_id, email_count, mailbox_limit, email_limit):
    from app.blueprints.parse.models.mailbox import Mailbox
    from app.blueprints.parse.models.email import Email

    # Get the current count of mailboxes and emails
    mailbox_count = Mailbox.query.filter(Mailbox.user_email == email).count()
    # email_count = Email.query.filter(Email.user_email == email).count()

    # Get the counts of how many emails and mailboxes will be deleted
    email_delete_count = email_count - email_limit if email_count > email_limit else 0
    mailbox_delete_count = mailbox_count - mailbox_limit if mailbox_count > mailbox_limit else 0

    # Get the list of mailboxes and emails to be deleted that are over the new limit
    # Set order_by to 'asc' for oldest mailboxes/emails and 'desc' for most recent
    mailboxes_to_delete = Mailbox.query.with_entities(Mailbox.id, Mailbox.mailbox_id).filter(Mailbox.user_email == email).order_by(Mailbox.created_on.desc()).limit(mailbox_delete_count).all()
    emails_to_delete = [e[0] for e in Email.query.with_entities(Email.id).filter(Email.user_email == email).order_by(Email.created_on.desc()).limit(email_delete_count).all()]

    # Delete the extra emails first
    emails_deleted = Email.bulk_delete(emails_to_delete)

    # Move leftover emails from mailboxes to be deleted to oldest mailbox
    for mailbox in mailboxes_to_delete:
        Email.query.filter(Email.mailbox_id == mailbox[1]).update({'mailbox_id':mailbox_id})

    # Delete the extra mailboxes
    mailboxes_deleted = Mailbox.bulk_delete([m[0] for m in mailboxes_to_delete])

    # If emails or mailboxes are at or past the limit,
    # then cap out the remaining emails and mailboxes
    if email_count >= email_limit:
        emails_remaining = email_limit
    else:
        emails_remaining = email_count - emails_deleted

    if mailbox_count >= mailbox_limit:
        mailboxes_remaining = mailbox_limit
    else:
        mailboxes_remaining = mailbox_count - mailboxes_deleted

    # Return the number of emails and mailboxes remaining
    return emails_remaining, mailboxes_remaining


@celery.task()
def get_mailboxes(email):
    from sqlalchemy import func
    from app.blueprints.parse.models.mailbox import Mailbox
    from app.blueprints.parse.models.email import Email

    mailboxes = Mailbox.query.with_entities(Mailbox.mailbox_id).filter(Mailbox.user_email == email).all()
    emails_count = db.session.query(Email.mailbox_id, func.count(Email.id)).filter(Email.user_email == email).group_by(Email.mailbox_id).all()

    return list(inner_join(mailboxes,emails_count))


def inner_join(a, b):
    key = itemgetter(0)
    a.sort(key=lambda x: (x, key))
    b.sort(key=lambda x: (x, key))
    for _, group in groupby(merge(a, b, key=key), key):
        row_a, row_b = next(group), next(group, None)
        if row_b is not None:
            yield row_a + row_b[1:]
        else:
            yield row_a + (0,0)[1:]


# Emails -------------------------------------------------------------------
async def email_query(mailbox_id):
    emails = []

    async with create_engine(user=current_app.config.get('SQLALCHEMY_USER'),
                             database=current_app.config.get('SQLALCHEMY_DATABASE'),
                             host=current_app.config.get('SQLALCHEMY_HOST'),
                             password=current_app.config.get('SQLALCHEMY_PASSWORD')) as engine:

        metadata = sa.MetaData()
        tbl = sa.Table('emails', metadata,
                       sa.Column('id', sa.Integer, primary_key=True),
                       sa.Column('mailbox_id', sa.String(255)),
                       sa.Column('sender', sa.String(255)),
                       sa.Column('subject', sa.String(255)),
                       sa.Column('date', sa.String(255)),
                       # sa.Column('body', sa.String(255)),
                       sa.Column('parsed', sa.Boolean),
                       sa.Column('autoparsed', sa.Boolean)
                       )

        query = tbl.select().where(tbl.c['mailbox_id'] == mailbox_id).order_by(tbl.c['date'])
        async with engine.acquire() as conn:
            async for row in conn.execute(query):
                emails.append({'id':row['id'],'sender':row['sender'],'subject':row['subject'],'date':row['date'],'parsed':row['parsed'],'autoparsed':row['autoparsed']})

    return list(reversed(emails))


async def asynchronous(mailbox_id):
    futures = await email_query(mailbox_id)

    return futures


def return_emails(mailbox_id):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    ioloop = asyncio.get_event_loop()

    emails = ioloop.run_until_complete(asynchronous(mailbox_id))
    emails = emails

    return emails


@celery.task()
def get_emails(mailbox_id):
    return return_emails(mailbox_id)


@celery.task()
def delete_emails(email):
    from app.blueprints.parse.models.email import Email
    Email.query.filter(Email.id == email).first().delete()


@celery.task()
def export_emails(mailbox_id):
    from app.blueprints.parse.models.email import Email
    return Email.query.filter(Email.mailbox_id == mailbox_id).filter(Email.parsed == True).all()


# Rules -------------------------------------------------------------------
@celery.task()
def get_rules(mailbox_id):
    rules = []
    from app.blueprints.parse.models.rule import Rule

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


@celery.task()
def delete_all(email, mailbox_id):
    from app.blueprints.parse.models.email import Email
    from app.blueprints.parse.models.mailbox import Mailbox
    from app.blueprints.parse.models.rule import Rule

    Email.query.filter_by(user_email=email).delete()
    Mailbox.query.filter_by(user_email=email).delete()
    Rule.query.filter_by(mailbox_id=mailbox_id).delete()


# Cache -------------------------------------------------------------------
@celery.task()
def set_cache(mailbox_id, emails_id):
    emails = get_emails.AsyncResult(emails_id)

    if emails.state != 'PENDING':
        cache.set(mailbox_id, emails.result)
    else:
        time.sleep(1)
        set_cache(mailbox_id, emails_id)


# Sending emails -------------------------------------------------------------------
@celery.task()
def send_welcome_email(email):
    from app.blueprints.user.templates.emails import send_welcome_email
    send_welcome_email(email)


@celery.task()
def send_plan_change_email(email, plan):
    from app.blueprints.user.templates.emails import send_plan_change_email
    send_plan_change_email(email, plan)


@celery.task()
def send_contact_us_email(email, message):
    from app.blueprints.user.templates.emails import contact_us_email
    contact_us_email(email, message)


@celery.task()
def send_cancel_email(email):
    from app.blueprints.user.templates.emails import send_cancel_email
    send_cancel_email(email)


@celery.task()
def send_export_email(email, csv):
    from app.blueprints.user.templates.emails import send_export_email
    send_export_email(email, csv)


