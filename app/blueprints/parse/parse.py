import re
from app.extensions import db
from flanker.addresslib import address
from app.blueprints.parse.models.email import Email
from app.blueprints.parse.models.rule import Rule
from app.blueprints.user.create_mailgun_user import generate_mailbox_id


def parse_email(msg):

    # Get headers.
    message_id = msg['Message-Id']
    mailbox_id = str(address.parse(msg['To'])).split("@")[0].upper()  # the user's mailgun inbox that it was sent to
    to = str(address.parse(msg['From']))  # the original recipient (who forwarded it to mailgun)
    subject = parse_subject(msg['Subject'], None)
    date = msg['Date']
    body = msg['body-plain'].strip()
    from_ = ''

    # Get the original sender.
    sender = re.search('From: (.+?)\n', msg['body-plain'])
    if sender:
        from_ = parse_from(str(address.parse(sender.group(1))), None) if address.parse(sender.group(1))\
            else parse_from(str(sender.group(1)), None)

    # Ensure that the user exists
    from app.blueprints.user.models import User
    u = db.session.query(db.exists().where(User.mailbox_id == mailbox_id)).scalar()

    # If the user is found, save the email to the db.
    if u:
        # Create the email
        e = Email()
        e.mailbox_id = mailbox_id
        e.message_id = message_id
        e.to = to
        e.subject = subject
        e.date = date
        e.body = body
        e.sender = from_
        e.parsed = 1

        # Add the email to the database
        db.session.add(e)
        db.session.commit()

    # return email_obj.


# Parsing rules -------------------------------------------------------------------
def parse_from(from_, options):
    if 'mailto' in from_:
        from_ = re.search('mailto:(.+?)]', from_).group(1)
    return from_


def parse_subject(subject, options):
    prefixes = ['FW: ', 'FWD: ', 'Fwd: ', 'fw: ', 'fwd: ']

    for prefix in prefixes:
        if subject.startswith(prefix):
            return subject[len(prefix):]
    return subject


def parse_to(to, options):
    return


def parse_body(body, options):
    return


def parse_cc(cc, options):
    return


def parse_headers(headers, options):
    return


# Get emails and rules -------------------------------------------------------------------
def get_emails(mailbox_id):
    return Email.query.filter(Email.mailbox_id == mailbox_id).all()


def get_rules(mailbox_id):
    return Rule.query.with_entities(Rule.rule, Rule.id).filter(Rule.mailbox_id == mailbox_id).all()


# Create test user and email -------------------------------------------------------------------
def create_test_user():
    from app.blueprints.user.models import User

    u = User()
    u.role = 'member'
    u.mailbox_id = generate_mailbox_id()

    return u


def create_test_email():
    e = Email()
    e.subject = "This is your first parsed email!"
    e.id = 0
    e.mailbox_id = 0
    e.message_id = "testemail@simpleytics.com"
    e.sender = "parser@simpleytics.com"
    e.to = "you@youremail.com"
    e.body = "This is a test email from the team over at Simpleytics.\n\nThis will give you an idea of what to expect" \
             "when it comes to parsing an email. Just select the section of the email that you want to parse, then the" \
             "parsing options that best fit your needs. After creating the parsing rule, you'll be able to apply it to" \
             "any emails that come to your inbox.\n\nThank you for using the email parser!\n\nSincerely,\n\nThe team at" \
             "Simpleytics."

    return e


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
