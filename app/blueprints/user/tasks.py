import time
import asyncio
from aiopg.sa import create_engine
from flask import current_app
import sqlalchemy as sa
from lib.flask_mailplus import send_template_message
from app.extensions import cache, db
from app.app import create_celery_app
from app.blueprints.user.models import User
from app.blueprints.parse.models.rule import Rule


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

    send_template_message(subject='Password reset from Parser',
                          recipients=[user.email],
                          template='user/mail/password_reset', ctx=ctx)

    return None


# User -------------------------------------------------------------------
@celery.task()
def adjust_mailboxes(email, mailbox_limit, email_limit):
    from app.blueprints.parse.models.mailbox import Mailbox
    from app.blueprints.parse.models.email import Email

    # Get the total count of mailboxes and emails
    mailbox_count = Mailbox.query.filter(Mailbox.user_email == email).count()
    email_count = Email.query.filter(Email.user_email == email).count()

    # Get the list of mailboxes and emails to be deleted that are over the new limit
    # Set order_by to 'asc' for oldest mailboxes/emails and 'desc' for most recent
    mailboxes_to_delete = [m[0] for m in Mailbox.query.with_entities(Mailbox.id).filter(Mailbox.user_email == email).order_by(Mailbox.created_on.desc()).limit(mailbox_count - mailbox_limit).all()]
    emails_to_delete = [e[0] for e in Email.query.with_entities(Email.id).filter(Email.user_email == email).order_by(Email.created_on.desc()).limit(email_count - email_limit).all()]

    # Delete the extra emails first
    Email.bulk_delete(emails_to_delete)

    # Move leftover emails from mailboxes to be deleted to oldest mailbox
    for mailbox in mailboxes_to_delete:
        print(mailbox)

    # Delete the extra mailboxes
    Mailbox.bulk_delete(mailboxes_to_delete)



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
                       )

        query = tbl.select().where(tbl.c['mailbox_id'] == mailbox_id)
        async with engine.acquire() as conn:
            async for row in conn.execute(query):
                # emails.update({row['id'] : {'id':row['id'],'sender':row['sender'],'subject':row['subject'],'date':row['date'],'parsed':row['parsed']}})
                emails.append({'id':row['id'],'sender':row['sender'],'subject':row['subject'],'date':row['date'],'parsed':row['parsed']})

    return emails


async def asynchronous(mailbox_id):
    futures = await email_query(mailbox_id)

    return futures


def return_emails(mailbox_id):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    ioloop = asyncio.get_event_loop()

    emails = ioloop.run_until_complete(asynchronous(mailbox_id))
    emails = list(reversed(emails))

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
    else:
        time.sleep(1)
        set_cache(mailbox_id, emails_id)

