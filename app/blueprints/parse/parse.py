import re
import os
import random
from app.extensions import db
from flanker.addresslib import address
from sqlalchemy.orm import load_only
from app.blueprints.parse.models.email import Email
from app.blueprints.parse.models.rule import Rule
from app.blueprints.user.create_mailgun_user import generate_mailbox_id


def parse_email(email_id, rules):

    # email = Email.query.filter(Email.id == email_id).first()

    for rule_id in rules:

        rule = Rule.query.filter(Rule.id == rule_id).first()
        section = rule.section
        category = rule.category
        options = rule.options
        args = rule.args.split(',')

        email = Email.query.filter(Email.id == email_id).first()

        parse(email, section, category, options, args)


# Parsing rules -------------------------------------------------------------------
def parse(email, section, category, options, args):
    if section == "from":
        result = parse_from(email, category, options, args)
        email.sender = result
    elif section == "to":
        result = parse_to(email, category, options, args)
        email.to = result
    elif section == "subject":
        result = parse_subject(email, category, options, args)
        email.subject = result
    elif section == "date":
        result = parse_date(email, category, options, args)
        email.date = result
    elif section == "body":
        result = parse_body(email, category, options, args)
        email.body = result#

    # email.parsed = 1
    # db.session.commit()

    # elif section == "CC":##
    #     parse_cc(email, category, options, args)
    # elif section == "Headers":
    #     parse_headers(email, category, options, args)


def parse_from(email, category, options, args):
    sender = email.sender
    if 'mailto' in sender:
        sender = re.search('mailto:(.+?)]', sender).group(1)
    if category == 'remove':
        return remove_parsing(sender, options, args)
    elif category == 'extract':
        return extract_parsing(sender, options, args)
    elif category == 'replace':
        return replace_parsing(sender, args)


def parse_subject(email, category, options, args):
    subject = email.subject
    if category == 'remove':
        return remove_parsing(subject, options, args)
    elif category == 'extract':
        return extract_parsing(subject, options, args)
    elif category == 'replace':
        return replace_parsing(subject, args)


def parse_to(email, category, options, args):
    to = email.to
    if category == 'remove':
        return remove_parsing(to, options, args)
    elif category == 'extract':
        return extract_parsing(to, options, args)
    elif category == 'replace':
        return replace_parsing(to, args)


def parse_date(email, category, options, args):
    date = email.date
    if category == 'remove':
        return remove_parsing(date, options, args)
    elif category == 'extract':
        return extract_parsing(date, options, args)
    elif category == 'replace':
        return replace_parsing(date, args)


def parse_body(email, category, options, args):
    body = email.body
    if category == 'remove':
        return remove_parsing(body, options, args)
    elif category == 'extract':
        return extract_parsing(body, options, args)
    elif category == 'replace':
        return replace_parsing(body, args)

# def parse_cc(email, category, options, args):
#     cc = email.cc
#
#
# def parse_headers(email, category, options, args):
#     headers = email.headers


# Parsing Categories -------------------------------------------------------------------
def remove_parsing(item, options, args):
    if options == "Remove specific content":
        return remove_parse(item, args)
    elif options == "Remove all links":
        return remove_links_parse(item)
    elif options == "Remove blank lines":
        return remove_blank_parse(item)


def extract_parsing(item, options, args):
    if options == "Find rows with certain text":
        return rows_parse(item, args)
    elif options == "Find all email addresses":
        return emails_parse(item)
    elif options == "Find content by line number":
        return line_numbers_parse(item, args)
    if options == "Find all text after selection":
        return text_after_parse(item, args)
    elif options == "Find all text before selection":
        return text_before_parse(item, args)
    elif options == "Find all URLs":
        return url_parse(item)


def replace_parsing(item, args):
    return find_replace_parse(item, args)


# Parsing Options -------------------------------------------------------------------
def rows_parse(item, args):
    results = []
    for arg in args:
        for line in item.split('\n'):
            if arg.strip() in line:
                results.append(line.strip())

    results = list(set(results))
    return results


# Works, email addresses aren't unique
def emails_parse(item):
    match = re.findall(r'[\w\.-]+@[\w\.-]+', item)
    return match


# Works
def line_numbers_parse(item, args):
    results = []
    for arg in args:
        count = 1
        for line in item.split('\n'):
            if str(count) == arg.strip():
                results.append(line)
            count += 1

    results = list(set(results))
    return results


# Working
def text_after_parse(item, args):
    results = []
    for arg in args:
        index = re.search(arg.strip(), item, re.IGNORECASE).end()
        results.append(item[index:])

    return results


# Working
def text_before_parse(item, args):
    results = []
    for arg in args:
        index = re.search(arg.strip(), item, re.IGNORECASE).start
        results.append(item[:index])

    return results


# Needs work
def url_parse(item):
    result = re.findall('https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', item)
    print(result)##
    return result


# Working
def find_replace_parse(item, *args):
    for arg in args:
        item = item.replace(arg[0].split('(', 1)[1].strip(), arg[1].split(')', 1)[0].strip())
    return item


# Working
def remove_parse(item, args):
    for arg in args:
        item = item.replace(arg, "")
    return item


# Working
def remove_links_parse(item):
    result = re.sub(r"http\S+", "", item)
    result = re.sub(r"https\S+", "", result)
    return result


# Needs work
def remove_blank_parse(item):
    item = os.linesep.join([s for s in item.splitlines() if s])
    print(item)#
    return item


# Get emails and rules -------------------------------------------------------------------
def get_rule_options(rule):
    if rule == 'extract':
        return random.choice(['Find rows with certain text', 'Find all email addresses', 'Find content by line number',
                              'Find all text after selection', 'Find all text before selection', 'Find all URLs'])
    elif rule == 'remove':
        return random.choice(['Remove specific content', 'Remove all links', 'Remove blank lines'])
    else:
        return 'Find and replace content'


# Create objects -------------------------------------------------------------------
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
