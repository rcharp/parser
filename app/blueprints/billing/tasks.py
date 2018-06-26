from app.app import create_celery_app
from app.blueprints.user.models import User
from app.blueprints.billing.models.credit_card import CreditCard
from app.blueprints.billing.views.billing import cancel

celery = create_celery_app()


@celery.task()
def mark_old_credit_cards():
    """
    Mark credit cards that are going to expire soon or have expired.

    :return: Result of updating the records
    """
    return CreditCard.mark_old_credit_cards()


@celery.task()
def delete_users(ids):
    """
    Delete users and potentially cancel their subscription.

    :param ids: List of ids to be deleted
    :type ids: list
    :return: int
    """
    return User.bulk_delete(ids)


@celery.task()
def cancel():
    return cancel
