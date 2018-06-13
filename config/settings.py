from datetime import timedelta
import os
from celery.schedules import crontab


DEBUG = True
LOG_LEVEL = 'DEBUG'  # CRITICAL / ERROR / WARNING / INFO / DEBUG

SECRET_KEY = os.environ.get('SECRET_KEY', None)

# Flask-Mail.
MAIL_USERNAME = os.environ.get('MAIL_USERNAME', None)
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', None)
MAIL_DEFAULT_SENDER = os.environ.get('MAIL_USERNAME', None)
MAIL_SERVER = os.environ.get('MAIL_SERVER', None)
MAIL_PORT = 465
MAIL_USE_TLS = False
MAIL_USE_SSL = True

# Cache
CACHE_TYPE = 'redis'
CACHE_REDIS_HOST = os.environ.get('CACHE_REDIS_HOST', None)
CACHE_REDIS_PASSWORD = os.environ.get('CACHE_REDIS_PASSWORD', None)
CACHE_DEFAULT_TIMEOUT = os.environ.get('CACHE_DEFAULT_TIMEOUT', None)
CACHE_REDIS_PORT = os.environ.get('CACHE_REDIS_PORT', None)
CACHE_REDIS_URL = os.environ.get('CACHE_REDIS_URL', None)

# Celery.
CELERY_BROKER_URL = os.environ.get('CACHE_REDIS_URL', None)
CELERY_RESULT_BACKEND = os.environ.get('CACHE_REDIS_URL', None)
CELERY_REDIS_URL = os.environ.get('CACHE_REDIS_URL', None)
CELERY_REDIS_HOST = os.environ.get('CACHE_REDIS_HOST', None)
CELERY_REDIS_PORT = os.environ.get('CACHE_REDIS_PORT', None)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_RESULT_EXPIRES = 300
CELERY_REDIS_MAX_CONNECTIONS = 99999
CELERYBEAT_SCHEDULE = {
    'mark-soon-to-expire-credit-cards': {
        'task': 'app.blueprints.billing.tasks.mark_old_credit_cards',
        'schedule': crontab(hour=0, minute=0)
    },
}

# SQLAlchemy.
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', None)
SQLALCHEMY_TRACK_MODIFICATIONS = False

# User.
SEED_ADMIN_EMAIL = os.environ.get('SEED_ADMIN_EMAIL', None)
SEED_ADMIN_PASSWORD = os.environ.get('SEED_ADMIN_PASSWORD', None)
REMEMBER_COOKIE_DURATION = timedelta(days=90)

# Turn off debug intercepts
DEBUG_TB_INTERCEPT_REDIRECTS = False
DEBUG_TB_ENABLED = False

# Billing.
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', None)
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', None)
STRIPE_API_VERSION = '2018-02-28'
STRIPE_AUTHORIZATION_LINK = os.environ.get('STRIPE_CONNECT_AUTHORIZE_LINK', None)
STRIPE_PLANS = {
    '0': {
        'id': 'hobby',
        'name': 'Hobby',
        'amount': 900,
        'currency': 'usd',
        'interval': 'month',
        'interval_count': 1,
        'trial_period_days': 14,
        'statement_descriptor': 'HOBBY',
        'metadata': {}
    },
    '1': {
        'id': 'startup',
        'name': 'Startup',
        'amount': 3900,
        'currency': 'usd',
        'interval': 'month',
        'interval_count': 1,
        'trial_period_days': 14,
        'statement_descriptor': 'STARTUP',
        'metadata': {
            'recommended': True
        }
    },
    '2': {
        'id': 'professional',
        'name': 'Professional',
        'amount': 9900,
        'currency': 'usd',
        'interval': 'month',
        'interval_count': 1,
        'trial_period_days': 14,
        'statement_descriptor': 'PROFESSIONAL',
        'metadata': {}
    },
    '3': {
        'id': 'enterprise',
        'name': 'Enterprise',
        'amount': 24900,
        'currency': 'usd',
        'interval': 'month',
        'interval_count': 1,
        'trial_period_days': 14,
        'statement_descriptor': 'ENTERPRISE',
        'metadata': {}
    },
    '4': {
        'id': 'developer',
        'name': 'Developer',
        'amount': 1,
        'currency': 'usd',
        'interval': 'month',
        'interval_count': 1,
        'trial_period_days': 0,
        'statement_descriptor': 'DEVELOPER',
        'metadata': {}
    }
}