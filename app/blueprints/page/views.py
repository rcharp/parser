from flask import Blueprint, render_template
from app.extensions import cache, timeout
from config import settings
from flask import redirect, url_for
from flask_login import current_user

page = Blueprint('page', __name__, template_folder='templates')


@page.route('/')
@cache.cached(timeout=timeout)
def home():
    if current_user.is_authenticated:
        return redirect(url_for('user.settings'))
    return render_template('/page/welcome.html',
                           plans=settings.STRIPE_PLANS)


@page.route('/table')
@cache.cached(timeout=timeout)
def table():
    return render_template('page/table.html')


@page.route('/terms')
@cache.cached(timeout=timeout)
def terms():
    return render_template('page/terms.html')


@page.route('/privacy')
@cache.cached(timeout=timeout)
def privacy():
    return render_template('page/privacy.html')


@page.route('/demo', methods=['GET','POST'])
@cache.cached(timeout=timeout)
def demo():
    email_list = []
    # emails = get_emails()

    # for email in emails:
    #     parse_email(email, email_list)

    # email_list.append(parse_email(get_emails()))

    # create_user()

    return render_template('page/demo.html', emails=email_list)


@page.route('/index')
def index():
    return render_template('page/index.html')
