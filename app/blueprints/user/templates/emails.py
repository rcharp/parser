__author__ = 'Ricky'
from flask import Flask, render_template
from flask_mail import Mail, Message
from app.app import create_celery_app

celery = create_celery_app()


def send_welcome_email(email):
    app = Flask(__name__)
    mail = Mail()
    mail.init_app(app)
    msg = Message("You've successfully signed up for Parsavvy!",
                  sender="support@parsavvy.com",
                  recipients=[email])

    msg.html = render_template('user/mail/welcome_email.html')

    mail.send(msg)

    print("Email was sent successfully")


def send_plan_change_email(email, plan):
    app = Flask(__name__)
    mail = Mail()
    mail.init_app(app)
    msg = Message("Your plan with Parsavvy has been changed.",
                  sender="support@parsavvy.com",
                  recipients=[email])
    if plan == 'Hobby':
        amount = 25
    elif plan == 'Startup':
        amount = 50
    elif plan == 'Professional':
        amount = 150
    else:
        amount = 250
    msg.html = render_template('user/mail/plan_change_email.html', plan=plan, amount=amount)

    mail.send(msg)


def contact_us_email(email, message):
    app = Flask(__name__)
    mail = Mail()
    mail.init_app(app)
    msg = Message("[Parsavvy Contact] Support request from " + email,
                  recipients=["support@parsavvy.com"],
                  sender="support@parsavvy.com",
                  reply_to=email)
    msg.body = email + " sent you a message:\n\n" + message

    response = Message("Your email to Parsavvy has been received.",
                       recipients=[email],
                       sender="support@parsavvy.com")

    response.html = render_template('user/mail/contact_email.html',email=email, message=message)

    mail.send(msg)
    mail.send(response)


def send_cancel_email(email):
    app = Flask(__name__)
    mail = Mail()
    mail.init_app(app)
    msg = Message("Goodbye from Parsavvy",
                  sender="support@parsavvy.com",
                  recipients=[email])

    msg.html = render_template('user/mail/cancel_email.html')

    mail.send(msg)


def send_export_email(email, csv):

    app = Flask(__name__)
    mail = Mail()
    mail.init_app(app)
    msg = Message("Your data export from Parsavvy",
                  sender="support@parsavvy.com",
                  recipients=[email])

    msg.html = render_template('user/mail/export_email.html')
    msg.attach("Parsed_data.csv", "text/csv", csv)

    mail.send(msg)
