import string
import random
import requests
from app.extensions import db
from sqlalchemy import exists
from flask_login import current_app


def generate_mailbox_id(user, size=8, chars=string.ascii_uppercase + string.digits):

    # Generate a random 8-character user id
    mailbox_id = ''.join(random.choice(chars) for _ in range(size))

    # Check to make sure there isn't already that id in the database
    if not db.session.query(exists().where(user.mailbox_id == mailbox_id)).scalar():
        return mailbox_id
    else:
        generate_mailbox_id()


# Creates login credentials for users' inboxes
def create_inbox(mailbox_id):
        url = "https://api.mailgun.net/v3/domains/" + current_app.config.get('MAILGUN_DOMAIN') + "/credentials"

        return requests.post(url, auth=("api", current_app.config.get('MAILGUN_API_KEY')),
                          data={"login": mailbox_id, "password": current_app.config.get('MAILGUN_PASSWORD')})


# def create_route(mailbox_id):
#     url = "https://api.mailgun.net/v3/domains/" + current_app.config.get('MAILGUN_DOMAIN') + "/routes"
#     return requests.post(url, auth=("api", current_app.config.get('MAILGUN_API_KEY')),
#                          data={"priority": 0,
#                                "expression": "match_recipient('.*@YOUR_DOMAIN_NAME')",
#                                "action": ["forward('http://myhost.com/messages/')", "stop()"]})

def create_user():
    url = "https://api.mailgun.net/v3/domains/" + current_app.config.get('MAILGUN_DOMAIN') + "/credentials"

    r = requests.post(url, auth=("api", current_app.config.get('MAILGUN_API_KEY')),
                      data={"login": current_app.config.get('MAILGUN_LOGIN'),"password": current_app.config.get('MAILGUN_PASSWORD')})
