import click
import random

from sqlalchemy_utils import database_exists, create_database

from app.app import create_app
from app.extensions import db
from app.blueprints.user.models import User
from app.blueprints.parse.parse import get_rule_options

# Create an app context for the database connection.
app = create_app()
db.app = app


@click.group()
def cli():
    """ Run PostgreSQL related tasks. """
    pass


@click.command()
@click.option('--with-testdb/--no-with-testdb', default=False,
              help='Create a test db too?')
def init(with_testdb):
    """
    Initialize the database.

    :param with_testdb: Create a test database
    :return: None
    """
    db.drop_all()
    # add the emails table to the db
    from app.blueprints.parse.models.email import Email
    from app.blueprints.parse.models.mailbox import Mailbox
    from app.blueprints.parse.models.rule import Rule
    from app.blueprints.user.models import User

    db.create_all()

    if with_testdb:
        db_uri = '{0}_test'.format(app.config['SQLALCHEMY_DATABASE_URI'])

        if not database_exists(db_uri):
            create_database(db_uri)

    # Create a test user for the db
    # from app.blueprints.parse.parse import create_test_user
    #
    # user = create_test_user()
    # user.email = app.config['SEED_MEMBER_EMAIL']
    # user.password = User.encrypt_password(app.config['SEED_ADMIN_PASSWORD'])
    #
    # user.save()

    # from app.blueprints.parse.models.rule import Rule
    #
    # # Create default rules
    # rules = ['From', 'To', 'Subject', 'Date']
    #
    # for rule in rules:
    #     r = Rule()
    #     r.mailbox_id = user.mailbox_id
    #     r.section = rule
    #     r.name = 'Parsing rule for section: ' + rule
    #     r.category = random.choice(['extract', 'replace', 'remove'])
    #     r.options = get_rule_options(r.category)
    #     r.save()

    # db.session.add(user)
    # db.session.commit()

    return None


@click.command()
def seed():
    """
    Seed the database with an initial user.

    :return: User instance
    """
    if User.find_by_identity(app.config['SEED_ADMIN_EMAIL']) is not None:
        return None

    params = {
        'role': 'admin',
        'email': app.config['SEED_ADMIN_EMAIL'],
        'password': app.config['SEED_ADMIN_PASSWORD']
    }

    # test = {
    #     'role' : 'member',
    #     'email': app.config['SEED_MEMBER_EMAIL'],
    #     'password': app.config['SEED_ADMIN_PASSWORD']
    # }

    return User(**params).save()


@click.command()
@click.option('--with-testdb/--no-with-testdb', default=False,
              help='Create a test db too?')
@click.pass_context
def reset(ctx, with_testdb):
    """
    Init and seed automatically.

    :param with_testdb: Create a test database
    :return: None
    """
    ctx.invoke(init, with_testdb=with_testdb)
    ctx.invoke(seed)

    return None


cli.add_command(init)
cli.add_command(seed)
cli.add_command(reset)