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

        from app.blueprints.parse.parse import parse_subject

        # Get headers.
        message_id = data['Message-Id']
        mailbox_id = str(address.parse(data['To'])).split("@")[0].upper()  # the user's mailgun inbox that it was sent to
        subject = parse_subject(data['Subject'], None)
        date = data['Date']
        from_ = ''
        body = data['body-plain']

        # Get the original sender.
        sender = re.search('From: (.+?)\n', data['body-plain'])
        if sender:
            from_ = parse_from(str(address.parse(sender.group(1))), None) if address.parse(sender.group(1)) \
                else parse_from(str(sender.group(1)), None)

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
            e.sender = from_
            e.body = body

            # Add the email to the database
            db.session.add(e)
            db.session.commit()

        # parse_email(data)

        return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
