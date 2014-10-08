import os

# Abs path of current file
basedir = os.path.abspath(os.path.dirname(__file__))

DEBUG = True

ADMINS = [
    {
        'email': 'test@test.com',
        'password': 'test',
        'author_id': 'imods.test'
    }
]

DEFAULT_CATEGORIES = [
    {
        'name': 'featured',
        'description': 'featured apps',
    },
]

UPLOAD_PATH = "/tmp/imods"

SECRET_KEY = 'somescretkey'  # Replace this in production

SQLITE_DB_PATH = os.path.join(basedir, 'imods.db')

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + SQLITE_DB_PATH
DATABASE_CONNECT_OPTIONS = {}

CSRF_ENABLED = True
CSRF_SESSION_KEY = "somethingimpossibletoguess"

BOTO_PROFILE = 'imods_testing'

STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY')
