import re
import json
from app.extensions import db
from flanker.addresslib import address
from flask import Blueprint, request
from app.extensions import csrf

parse = Blueprint('parse', __name__, template_folder='templates')


@parse.route('/incoming', methods=['GET','POST'])
@csrf.exempt
def incoming():
    if request.form:

        # Get the mailbox id from the email
        data = request.form
        mailbox_id = str(address.parse(data['recipient'] or data['Recipient'])).split("@")[0].upper()  # the user's mailgun inbox that it was sent to

        # Get the user and their email limits
        from app.blueprints.user.models import User
        from app.blueprints.parse.models.mailbox import Mailbox
        from app.blueprints.parse.models.email import Email
        user = Mailbox.query.with_entities(Mailbox.user_email).filter(Mailbox.mailbox_id == mailbox_id).first()

        if user:
            count = User.query.with_entities(User.email_count).filter(User.email == user).scalar()
            limit = User.query.with_entities(User.email_limit).filter(User.email == user).scalar()

            if count and limit:
                if count < limit:

                    # Get headers.
                    message_id = data['Message-Id'] if 'Message-Id' in data else None
                    subject = clean_subject(data['Subject']) if 'Subject' in data else None
                    to = data['Sender'] if 'Sender' in data else None
                    date = data['Date'].split(' -')[0] if 'Date' in data else None
                    cc = data['Cc'] if 'cc' in data else None
                    body = clean_body(data['body-plain'].strip()) if 'body-plain' in data else None

                    # Get the original sender..
                    sender = re.search('From: (.+?)\n', data['body-plain'])
                    if sender:
                        sender = clean_sender(str(address.parse(sender.group(1)))) if address.parse(sender.group(1)) \
                            else clean_sender(str(sender.group(1)))

                    # Ensure that the user exists and get the user
                    u = db.session.query(db.exists().where(User.mailbox_id == mailbox_id)).scalar()
                    user = User.query.filter(User.mailbox_id == mailbox_id).first()

                    # If the user is found, save the email to the db.
                    if u:
                        from app.blueprints.parse.models.email import Email
                        # Create the email
                        e = Email()
                        e.mailbox_id = mailbox_id
                        e.message_id = message_id
                        e.user_email = user.email
                        e.subject = subject
                        e.date = date
                        e.sender = sender
                        e.to = to
                        e.cc = cc
                        e.body = body

                        # Add the email to the database
                        db.session.add(e)
                        db.session.commit()

                        # Update the user's email count
                        user.email_count += 1
                        user.save()

        return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


def clean_subject(subject):
    prefixes = ['FW: ', 'FWD: ', 'Fwd: ', 'fw: ', 'fwd: ']

    for prefix in prefixes:
        if subject.startswith(prefix):
            return subject[len(prefix):]
    return subject


def clean_sender(sender):
    if 'mailto' in sender:
        sender = re.search('mailto:(.+?)]', sender).group(1)

    return sender


def clean_body(body):
    result = ''
    for line in body.split('\n'):
        if line.strip().startswith('>'):
            line = line.strip()[2:]
        result += line + '\n'
    return result
