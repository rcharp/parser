import datetime
from collections import OrderedDict
from hashlib import md5

import pytz
from flask import current_app
from sqlalchemy import or_
from werkzeug.security import generate_password_hash, check_password_hash

from flask_login import UserMixin

from itsdangerous import URLSafeTimedSerializer, \
    TimedJSONWebSignatureSerializer

from lib.util_sqlalchemy import ResourceMixin, AwareDateTime
from app.blueprints.user.models import User
from app.blueprints.billing.models.subscription import Subscription
from app.blueprints.billing.models.invoice import Invoice
from app.extensions import db


class Rule(UserMixin, ResourceMixin, db.Model):

    __tablename__ = 'rules'
    # Relationships.
    mailbox_id = db.Column(db.Integer, db.ForeignKey('users.id', onupdate='CASCADE', ondelete='CASCADE'),
                        index=True, nullable=False)

    # Rules.
    rules = db.Column(db.String(255), unique=False, index=True, nullable=True, server_default='')

    def __init__(self, **kwargs):
        # Call Flask-SQLAlchemy's constructor.
        super(Rule, self).__init__(**kwargs)

    @classmethod
    def find_by_id(cls, identity):
        """
        Find a set of rules by user id.

        :param identity: Email or username
        :type identity: str
        :return: User instance
        """
        return Rule.query.filter(
          (Rule.mailbox_id == identity).first())

    @classmethod
    def search(cls, query):
        """
        Search a resource by 1 or more fields.

        :param query: Search query
        :type query: str
        :return: SQLAlchemy filter
        """
        if not query:
            return ''

        search_query = '%{0}%'.format(query)
        search_chain = (Rule.message_id.ilike(search_query))

        return or_(*search_chain)

    @classmethod
    def bulk_delete(cls, ids):
        """
        Override the general bulk_delete method because we need to delete them
        one at a time while also deleting them on Stripe.

        :param ids: List of ids to be deleted
        :type ids: list
        :return: int
        """
        delete_count = 0

        for id in ids:
            rule = Rule.query.get(id)

            if rule is None:
                continue

            rule.delete()

            delete_count += 1

        return delete_count
