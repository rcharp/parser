__author__ = 'Ricky'

from app.blueprints.simple.date import datetime_to_int
from app.blueprints.simple.eventClass import Event
from app.blueprints.simple.date import one_month_ago, now, pretty_date
from random import randint
import datetime
import random


def random_date(start, end):
    return start + datetime.timedelta(seconds=randint(0, int((end - start).total_seconds())))


types = ["charge.failed", "charge.refunded", "charge.succeeded","customer.subscription.created",
         "customer.subscription.deleted", "customer.subscription.updated"]

demo_types = ["charge.failed", "charge.refunded", "charge.succeeded","customer.subscription.created",
              "customer.subscription.deleted", "Upgrade", "Downgrade"]

names = ["Someone", "Somebody", "A Customer", "A Company", "Someone Else", "Another Customer", "Somebody Else"]

plans = ["Parser Startup Plan", "Parser Professional Plan", "Parser Enterprise Plan"]

amounts = [39, 79, 149]


def create_demo():
    demo_list = []
    for x in range(9):

        event = Event()
        event.type = "charge.succeeded"
        event.name = random.choice(names)
        event.dateint = datetime_to_int(random_date(one_month_ago, now).timetuple())
        event.p_date = pretty_date(event.dateint)
        event.plan = random.choice(plans)
        event.amount = random.choice(amounts)

        demo_list.append(event)

    for x in range(3):
        event = Event()
        event.type = "Upgrade"
        event.name = random.choice(names)
        event.dateint = datetime_to_int(random_date(one_month_ago, now).timetuple())
        event.p_date = pretty_date(event.dateint)
        event.plan = random.choice(plans)
        event.amount = random.choice(amounts)

        demo_list.append(event)

    for x in range(2):
        event = Event()
        event.type = "charge.refunded"
        event.name = random.choice(names)
        event.dateint = datetime_to_int(random_date(one_month_ago, now).timetuple())
        event.p_date = pretty_date(event.dateint)
        event.plan = random.choice(plans)
        event.amount = -random.choice(amounts)

        demo_list.append(event)

    for x in range(1):
        event = Event()
        event.type = "customer.subscription.deleted"
        event.name = random.choice(names)
        event.dateint = datetime_to_int(random_date(one_month_ago, now).timetuple())
        event.p_date = pretty_date(event.dateint)
        event.plan = random.choice(plans)
        event.amount = -random.choice(amounts)

        demo_list.append(event)

    demo_list.sort(key=lambda x: x.dateint, reverse=True)

    return demo_list
