from sqlalchemy import or_

from lib.util_sqlalchemy import ResourceMixin
from app.extensions import db


class Mailbox(ResourceMixin, db.Model):

    __tablename__ = 'mailboxes'

    # Relationships.
    email = db.Column(db.String(255), db.ForeignKey('users.email', onupdate='CASCADE', ondelete='CASCADE'),
                        index=True, nullable=True, primary_key=False, unique=False)

    # Objects.
    id = db.Column(db.Integer, primary_key=True)
    mailbox_id = db.Column(db.String(255), unique=True, index=True, nullable=True, server_default='')

    def __init__(self, **kwargs):
        # Call Flask-SQLAlchemy's constructor.
        super(Mailbox, self).__init__(**kwargs)