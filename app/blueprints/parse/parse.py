import re
import csv
import random
from app.extensions import db
from app.blueprints.parse.models.email import Email
from app.blueprints.parse.models.rule import Rule
from io import StringIO


def parse_email(email_id, rules):

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
        if result is not None:
            if category == 'extract':
                for item in result:
                    email.extracted_data += item + '\n'
            else:
                email.sender = result
    elif section == "to":
        result = parse_to(email, category, options, args)
        if result is not None:
            if category == 'extract':
                for item in result:
                    email.extracted_data += item + '\n'
            else:
                email.to = result
    elif section == "subject":
        result = parse_subject(email, category, options, args)
        if result is not None:
            if category == 'extract':
                for item in result:
                    email.extracted_data += item + '\n'
            else:
                email.subject = result
    elif section == "date":
        result = parse_date(email, category, options, args)
        if result is not None:
            if category == 'extract':
                for item in result:
                    email.extracted_data += item + '\n'
            else:
                email.date = result
    elif section == "body":
        result = parse_body(email, category, options, args)
        if result is not None:
            if category == 'extract':
                for item in result:
                    email.extracted_data += item + '\n'
            else:
                email.body = result
    elif section == "CC":
        result = parse_cc(email, category, options, args)
        if result is not None:
            if category == 'extract':
                for item in result:
                    email.extracted_data += item + '\n'
            else:
                email.cc = result
    elif section == "Headers":
        result = parse_headers(email, category, options, args)
        if result is not None:
            if category == 'extract':
                for item in result:
                    email.extracted_data += item + '\n'
            else:
                email.headers = result

    email.parsed = 1
    db.session.commit()


def parse_from(email, category, options, args):
    sender = email.sender

    if sender is None: return

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

    if subject is None: return

    if category == 'remove':
        return remove_parsing(subject, options, args)
    elif category == 'extract':
        return extract_parsing(subject, options, args)
    elif category == 'replace':
        return replace_parsing(subject, args)


def parse_to(email, category, options, args):
    to = email.to

    if to is None: return

    if category == 'remove':
        return remove_parsing(to, options, args)
    elif category == 'extract':
        return extract_parsing(to, options, args)
    elif category == 'replace':
        return replace_parsing(to, args)


def parse_date(email, category, options, args):
    date = email.date

    if date is None: return

    if category == 'remove':
        return remove_parsing(date, options, args)
    elif category == 'extract':
        return extract_parsing(date, options, args)
    elif category == 'replace':
        return replace_parsing(date, args)


def parse_body(email, category, options, args):
    body = email.body

    if body is None: return

    if category == 'remove':
        return remove_parsing(body, options, args)
    elif category == 'extract':
        return extract_parsing(body, options, args)
    elif category == 'replace':
        return replace_parsing(body, args)


def parse_cc(email, category, options, args):
    cc = email.cc

    if cc is None: return

    if category == 'remove':
        return remove_parsing(cc, options, args)
    elif category == 'extract':
        return extract_parsing(cc, options, args)
    elif category == 'replace':
        return replace_parsing(cc, args)


def parse_headers(email, category, options, args):
    headers = email.headers

    if headers is None: return

    if category == 'remove':
        return remove_parsing(headers, options, args)
    elif category == 'extract':
        return extract_parsing(headers, options, args)
    elif category == 'replace':
        return replace_parsing(headers, args)


# Parsing Categories -------------------------------------------------------------------
def remove_parsing(item, options, args):
    if options == "Remove specific content":
        return remove_parse(item, args)
    elif options == "Remove rows with specific content":
        return remove_rows_with_content_parse(item, args)
    elif options == "Remove rows that start with specific content":
        return remove_rows_start_with_content_parse(item, args)
    elif options == "Remove whitespace":
        return remove_whitespace_parse(item)
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
# Working
def rows_parse(item, args):
    results = []
    for arg in args:
        for line in item.split('\n'):
            if arg.lower().strip() in line.lower():
                results.append(line.strip())

    return list(set(results))


# Working
def emails_parse(item):
    results = re.findall(r'[\w\.-]+@[\w\.-]+', item)
    return list(set(results))


# Working
def line_numbers_parse(item, args):
    results = []
    for arg in args:
        count = 1
        for line in item.split('\n'):
            if str(count) == arg.strip():
                results.append(line)
            count += 1

    return list(set(results))


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
def remove_rows_with_content_parse(item, args):
    result = ''
    for line in item.split('\n'):
        for arg in args:
            if arg in line:
                pass
            else:
                result += line + '\n'
    return result


# Working
def remove_rows_start_with_content_parse(item, args):
    result = ''
    for line in item.split('\n'):
        for arg in args:
            if not line.startswith(arg):
                result += line + '\n'
    return result


# Working
def remove_whitespace_parse(item):
    result = ''
    for line in item.split('\n'):
        result += " ".join(line.split())
        result += '\n'
    return result


# Working
def remove_links_parse(item):
    result = re.sub(r"<http\S+", "", item)
    result = re.sub(r"<https\S+", "", result)
    return result


# Working
def remove_blank_parse(item):
    result = ''
    for line in item.split('\n'):
        if not re.match(r'^\s*$', line) and line.rstrip() != '>':
            result += line + '\n'

    return result


# Get rule options -------------------------------------------------------------------
def get_rule_options(rule):
    if rule == 'extract':
        return random.choice(['Find rows with certain text', 'Find all email addresses', 'Find content by line number',
                              'Find all text after selection', 'Find all text before selection', 'Find all URLs'])
    elif rule == 'remove':
        return random.choice(['Remove specific content', 'Remove all links', 'Remove blank lines'])
    else:
        return 'Find and replace content'


# Get rule options -------------------------------------------------------------------
def generate_csv(emails):

    buffer = StringIO()

    writer = csv.DictWriter(buffer, fieldnames=["Message Id", "From", "Cc", "Subject", "Date", "Body", "Extracted Data"])
    writer.writeheader()

    for email in emails:
        writer.writerow({"Message Id": email.message_id, "From": email.sender, "Cc": email.cc, "Subject": email.subject,
                         "Date": email.date, "Body": email.body, "Extracted Data": email.extracted_data})

    return buffer.getvalue()


# Create objects -------------------------------------------------------------------
def create_test_user():
    from app.blueprints.user.models import User

    u = User()
    u.role = 'member'
    # u.mailbox_id = generate_mailbox_id()

    return u


def create_test_email():
    e = Email()
    e.subject = "This is your first parsed email!"
    e.id = 0
    e.mailbox_id = 0
    e.message_id = "testemail@parsavvy.com"
    e.sender = "team@parsavvy.com"
    e.to = "you@youremail.com"
    e.body = "This is a test email from the team over at Parsavvy.\n\nThis will give you an idea of what to expect" \
             "when it comes to parsing an email. Just select the section of the email that you want to parse, then the" \
             "parsing options that best fit your needs. After creating the parsing rule, you'll be able to apply it to" \
             "any emails that come to your inbox.\n\nThank you for using Parsavvy!\n\nSincerely,\n\nThe team at" \
             "Parsavvy."

    return e
