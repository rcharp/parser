import re
import json
from flask import Blueprint, request
from app.extensions import csrf
from app.blueprints.parse.parse import parse_email
from flask_login import (
   current_user)

parse = Blueprint('parse', __name__, template_folder='templates')


@parse.route('/incoming', methods=['GET','POST'])
@csrf.exempt
def incoming():
    if request.form:
        data = request.form

        # # Get the original sender.
        # sender = re.search('From: (.+?)\n', data['body-plain'])
        #
        # if sender:
        #     print('Sender: ' + sender.group(1))
        #
        # print(data['message-headers']+'\n')
        # print('Message Id: ' + data['Message-Id'] + '\n')
        # print('From: ' + data['From'] + '\n')
        # print('User: ' + data['To'] + '\n')
        # print('Subject: ' + data['Subject'] + '\n')
        # print('Date: ' + data['Date'] + '\n')
        # print('Body: ' + data['body-plain'] + '\n')

        parse_email(data)

        return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
