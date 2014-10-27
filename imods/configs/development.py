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

UPLOAD_PATH = os.path.join(basedir, "deb")

CELERY_BROKER_URL = "amqp://imods:imodsmq@localhost/imods"

SECRET_KEY = 'somescretkey'  # Replace this in production

SQLITE_DB_PATH = os.path.join(basedir, 'imods.db')

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + SQLITE_DB_PATH
DATABASE_CONNECT_OPTIONS = {}

CSRF_ENABLED = True
CSRF_SESSION_KEY = "somethingimpossibletoguess"

BOTO_PROFILE = 'imods_testing'

S3_ASSETS_BUCKET = 'imods'
S3_PKG_BUCKET = 'imods_package'

PKG_INDEX_FILE_NAME = "Packages.gz"

# Download links expires in 30 minutes
DOWNLOAD_URL_EXPIRES_IN = 30*60

STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY')
