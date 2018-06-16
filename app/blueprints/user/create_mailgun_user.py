import string
import random
import requests
from app.extensions import db
from sqlalchemy import exists
from flask_login import current_app


def generate_mailbox_id(size=8, chars=string.ascii_uppercase + string.digits):

    # Generate a random 8-character user id
    mailbox_id = ''.join(random.choice(chars) for _ in range(size))

    from app.blueprints.user.models import User

    # Check to make sure there isn't already that id in the database
    if not db.session.query(exists().where(User.mailbox_id == mailbox_id)).scalar():
        return mailbox_id
    else:
        generate_mailbox_id()


# Creates login credentials for users' inboxes
def create_inbox(mailbox_id):
        url = "https://api.mailgun.net/v3/domains/" + current_app.config.get('MAILGUN_DOMAIN') + "/credentials"

        return requests.post(url, auth=("api", current_app.config.get('MAILGUN_API_KEY')),
                          data={"login": mailbox_id, "password": current_app.config.get('MAILGUN_PASSWORD')})
