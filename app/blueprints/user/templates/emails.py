__author__ = 'Ricky'
from flask import Flask, render_template
from flask_mail import Mail, Message


def send_welcome_email(email):
    app = Flask(__name__)
    mail = Mail()
    mail.init_app(app)
    msg = Message("You've successfully signed up for Parser!",
                  sender="support@parser.com",
                  recipients=[email])

    msg.html = render_template('user/mail/welcome_email.html')

    mail.send(msg)

    print("Email was sent successfully")


def send_plan_change_email(email, plan):
    app = Flask(__name__)
    mail = Mail()
    mail.init_app(app)
    msg = Message("Your plan with Parser has been changed.",
                  sender="support@parser.com",
                  recipients=[email])
    if plan == 'Startup':
        amount = 39
    elif plan == 'Professional':
        amount = 99
    else:
        amount = 249
    msg.html = render_template('user/mail/plan_change_email.html', plan=plan, amount=amount)

    mail.send(msg)


def contact_us_email(email, message):
    app = Flask(__name__)
    mail = Mail()
    mail.init_app(app)
    msg = Message("[Parser Contact] Support request from " + email,
                  recipients=["support@parser.com"],
                  sender="donotreply@parser.com",
                  reply_to=email)
    msg.body = email + " sent you a message:\n\n" + message

    response = Message("Your email to Parser has been received.",
                       recipients=[email],
                       sender="donotreply@parser.com")

    response.html = render_template('user/mail/contact_email.html',email=email, message=message)

    mail.send(msg)
    mail.send(response)


def send_cancel_email(email):
    app = Flask(__name__)
    mail = Mail()
    mail.init_app(app)
    msg = Message("Goodbye from Parser",
                  sender="support@parser.com",
                  recipients=[email])

    msg.html = render_template('user/mail/cancel_email.html')

    mail.send(msg)
