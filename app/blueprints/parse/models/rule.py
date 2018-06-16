from sqlalchemy import or_

from lib.util_sqlalchemy import ResourceMixin
from app.extensions import db


class Rule(ResourceMixin, db.Model):

    __tablename__ = 'rules'
    # Relationships.
    mailbox_id = db.Column(db.String(255), db.ForeignKey('users.mailbox_id', onupdate='CASCADE', ondelete='CASCADE'),
                           index=True, nullable=False, primary_key=False, unique=False)

    # Rules.
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.Text, nullable=True, server_default='')
    rule = db.Column(db.Text, nullable=True, default='')

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
