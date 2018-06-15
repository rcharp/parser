import imaplib
import re
import smtplib
import requests
from app.extensions import db
from flanker.addresslib import address
from flask import current_app
from flask_login import current_user
from app.blueprints.parse.models.email import Email


def parse_email(msg):

    # Get headers.
    message_id = msg['Message-Id']
    mailbox_id = address.parse(msg['To']).split("@")[0]  # the user's mailgun inbox that it was sent to
    recipient = address.parse(msg['From'])  # the original recipient (who forwarded it to mailgun)
    subject = msg['Subject']
    date = msg['Date']
    body = msg['body-plain']
    from_ = ''

    # Get the original sender.
    sender = re.search('From: (.+?)\n', msg['body-plain'])
    if sender:
        from_ = address.parse(sender.group(1))

    # Ensure that the user exists
    u = db.session.query(db.exists().where(current_user.mailbox_id == mailbox_id)).scalar()

    # If the user is found, save the email to the db
    if u:
        # Create the email
        e = Email()
        e.mailbox_id = u.mailbox_id
        e.message_id = message_id
        e.recipient = recipient
        e.subject = subject
        e.date = date
        e.body = body
        e.from_ = from_

        # Add the email to the database
        db.session.add(e)
        db.session.commit()

    # return email_obj


def get_emails(mailbox_id):

    return Email.query.filter(Email.mailbox_id == mailbox_id).all()

# <editor-fold desc="Old code">
# def get_emails():
#     emails = []
#     # mail = imaplib.IMAP4_SSL('imap.gmail.com')
#     #
#     # mail.login('rickycharpentier@gmail.com', 'hyrule724')
#     mail = smtplib.SMTP_SSL(current_app.config.get('MAILGUN_HOST'))
#     mail.login(current_app.config.get('MAILGUN_LOGIN'), current_app.config.get('MAILGUN_API_KEY'))
#
#     #mail.
#
#     result, data = mail.uid('search', None, "ALL")
#
#     # search and return uids instead.
#     x = 1  # number of email (in reverse order, recent first) Must be at least 1
#     i = len(data[0].split()) # data[0] is a space separate string
#     # for x in range(i-x, i):
#     latest_email_uid = data[0].split()[i-x]#[i-x] # unique ids wrt label selected
#     result, email_data = mail.uid('fetch', latest_email_uid, '(RFC822)')
#     # emails.sort(reverse=True)
#     return email_data
#     # return emails


# def old_parse_email(data, email_list):
#     body = ""
#     # fetch the email body (RFC822) for the given ID
#     raw_email = data[0][1]
#     email_string = raw_email.decode('utf-8')
#
#     try:
#         msg = email.message_from_string(email_string)
#     except UnicodeEncodeError:
#         msg = email.message_from_string(email_string.encode('ascii', 'ignore').decode('ascii').decode("utf-8"))
#
#     # for part in msg.walk():
#     #     if part.get_content_type() == "text/plain": # ignore attachments/html
#     #         body = part.get_payload(decode=True).decode("utf-8").replace('\n\n', '')
#     #         whole_body += body + " "
#     #     elif part.get_content_type() == "text/html": # handle html
#     #         body = BeautifulSoup(part.get_payload(decode=True).decode("utf-8"), 'html.parser').get_text().replace('\n\n', '')
#     #         whole_body += body + " "
#     #     if part.get_content_maintype() != 'multipart' and part.get('Content-Disposition') is not None:
#     #         pass  # Ignore images
#     #     else:
#     #         continue
#     if msg.is_multipart():
#         for payload in msg.get_payload():
#             soup = BeautifulSoup(payload.get_payload(decode=True).decode("utf-8"), 'html.parser')
#             [s.extract() for s in soup('style')] #  clean the css
#             try:
#                 body += soup.decode("utf-8").strip() + '\n'#.replace('\n', ' ')
#             except UnicodeEncodeError:
#                 body += soup.encode('ascii', 'ignore').decode('ascii').decode("utf-8").strip() + '\n'#.replace('\n', ' ')
#             break
#     else:
#         soup = BeautifulSoup(msg.get_payload(decode=True).decode("utf-8"), 'html.parser')
#         [s.extract() for s in soup('style')] #  clean the css
#         try:
#             body = soup.decode("utf-8").strip() + '\n'#.replace('\n', ' ')
#         except UnicodeEncodeError:
#             body = soup.encode('ascii', 'ignore').decode('ascii').decode("utf-8").strip() + '\n'#.replace('\n', ' ')
#
#     email_obj = e(msg['From'],msg['To'] if 'To' in msg else msg['Delivered-To'],msg['Subject'],msg['Date'],body)
#
#     # print('From: ' + email_obj.from_)
#     # print('To: ' + email_obj.to)
#     # print('Subject: ' + email_obj.subject)
#     # print('Date: ' + email_obj.date)
#     # print('Body: ' + email_obj.body)
#
#     email_list.append(email_obj)


# def old_parse_email2(data):
#     body = ""
#     raw_email = data[0][1]
#     email_string = raw_email.decode('utf-8')
#     msg = mime.from_string(email_string)
#
#     if msg.content_type.is_multipart():
#         for part in msg.parts:
#             body = part.body
#         soup = BeautifulSoup(body, 'html.parser')
#         [s.extract() for s in soup('style')]
#         body = soup.get_text()
#     elif msg.content_type.is_singlepart():
#         body = msg.body
#
#     # if msg.enclosed:
#     #     print(msg.enclosed)
#
#     email_obj = e(msg.message_id, address.parse(msg.headers['From']), msg.headers['To'], msg.headers['Subject'], msg.headers['Date'], body)
#
#     return email_obj
# </editor-fold>
