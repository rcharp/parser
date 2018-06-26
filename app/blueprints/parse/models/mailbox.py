from sqlalchemy import or_

from lib.util_sqlalchemy import ResourceMixin
from app.extensions import db


class Mailbox(ResourceMixin, db.Model):

    __tablename__ = 'mailboxes'

    # Relationships.
    user_email = db.Column(db.String(255), db.ForeignKey('users.email', onupdate='CASCADE', ondelete='CASCADE'),
                        index=True, nullable=True, primary_key=False, unique=False)

    # Objects.
    id = db.Column(db.Integer, primary_key=True)
    mailbox_id = db.Column(db.String(255), unique=True, index=True, nullable=True, server_default='')

    def __init__(self, **kwargs):
        # Call Flask-SQLAlchemy's constructor.
        super(Mailbox, self).__init__(**kwargs)

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
            mailbox = Mailbox.query.get(id)

            if mailbox is None:
                continue

            mailbox.delete()

            delete_count += 1

        return delete_count
