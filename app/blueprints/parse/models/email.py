import datetime

import pytz
from flask import current_app
from sqlalchemy import or_

from lib.util_sqlalchemy import ResourceMixin, AwareDateTime
from app.extensions import db


class Email(ResourceMixin, db.Model):

    __tablename__ = 'emails'

    # Relationships.
    mailbox_id = db.Column(db.Integer, db.ForeignKey('users.id', onupdate='CASCADE', ondelete='CASCADE'),
                        index=True, nullable=False, primary_key=True)

    # Parsed objects.
    message_id = db.Column(db.String(255), unique=False, index=True, nullable=True, server_default='')
    from_ = db.Column(db.String(255), unique=False, index=True, nullable=True, server_default='')
    recipient = db.Column(db.String(255), unique=False, index=True, nullable=True, server_default='')
    subject = db.Column(db.String(255), unique=False, index=True, nullable=True, server_default='')
    date = db.Column(db.String(255), unique=False, index=True, nullable=True, server_default='')
    body = db.Column(db.Text(), unique=False, index=True, nullable=True, server_default='')

    def __init__(self, **kwargs):
        # Call Flask-SQLAlchemy's constructor.
        super(Email, self).__init__(**kwargs)

    @classmethod
    def find_by_id(cls, identity):
        """
        Find an email by its message id.

        :param identity: Email or username
        :type identity: str
        :return: User instance
        """
        return Email.query.filter(
          (Email.message_id == identity).first())

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
        search_chain = (Email.message_id.ilike(search_query))

        return or_(*search_chain)

    @classmethod
    def get_all_emails(cls, ids):
        """
        Return all emails that are stored in the database

        :param ids: List of ids to be returned
        :type ids: list
        :return: list of emails
        """

        emails = []

        for id in ids:
            email = Email.query.get(id)

            if email is None:
                continue

            emails.append(email)

        return emails

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
            email = Email.query.get(id)

            if email is None:
                continue

            email.delete()

            delete_count += 1

        return delete_count
