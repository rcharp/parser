__author__ = 'Ricky'


class Event:
    def __init__(self,amount=None,dateint=None,date=None,# name=None,
                 type=None,plan=None,p_date=None):
                 # customer_id=None):
        self.amount = amount
        self.dateint = dateint
        self.date = date
        # self.name = name
        self.type = type
        self.plan = plan
        self.p_date = p_date
        # self.customer_id = customer_id