import re
import json
from app.extensions import db
from flanker.addresslib import address
from flask import Blueprint, request
from app.extensions import csrf
from app.blueprints.parse.parse import parse_from

parse = Blueprint('parse', __name__, template_folder='templates')


@parse.route('/incoming', methods=['GET','POST'])
@csrf.exempt
def incoming():
    if request.form:
        data = request.form

        # Get headers.
        message_id = data['Message-Id']
        mailbox_id = str(address.parse(data['To'])).split("@")[0].upper()  # the user's mailgun inbox that it was sent to
        subject = clean_subject(data['Subject'])
        date = data['Date']
        body = data['body-plain'].strip()

        # Get the original sender.
        sender = re.search('From: (.+?)\n', data['body-plain'])
        if sender:
            sender = clean_sender(str(address.parse(sender.group(1)))) if address.parse(sender.group(1)) \
                else clean_sender(str(sender.group(1)))

        # Ensure that the user exists
        from app.blueprints.user.models import User
        u = db.session.query(db.exists().where(User.mailbox_id == mailbox_id)).scalar()

        # If the user is found, save the email to the db.
        if u:
            from app.blueprints.parse.models.email import Email
            # Create the email
            e = Email()
            e.mailbox_id = mailbox_id
            e.message_id = message_id
            e.subject = subject
            e.date = date
            e.sender = sender
            e.body = body

            # Add the email to the database
            db.session.add(e)
            db.session.commit()

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
