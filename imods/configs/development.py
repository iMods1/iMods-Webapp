import os

CONFIG_NAME = "DEVELOPMENT"

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
        'name': 'Featured',
        'description': 'featured apps',
    },
    {
        'name': 'Tweaks',
        'description': 'featured apps',
    },
    {
        'name': 'Themes',
        'description': 'featured apps',
    },
    {
        'name': 'Free',
        'description': 'featured apps',
    },
    {
        'name': 'Paid',
        'description': 'featured apps',
    },
    {
        'name': 'Education',
        'description': 'featured apps',
    },
    {
        'name': 'Productivity',
        'description': 'featured apps',
    },
    {
        'name': 'Entertainment',
        'description': 'featured apps',
    },
    {
        'name': 'Games',
        'description': 'featured apps',
    },
    {
        'name': 'Business',
        'description': 'featured apps',
    },
    {
        'name': 'Aesthetics',
        'description': 'featured apps',
    },
    {
        'name': 'Functionality',
        'description': 'featured apps',
    },
    {
        'name': 'Performance',
        'description': 'featured apps',
    },
]

CACHE_CONFIG = {
    'CACHE_TYPE': 'simple',
}

TOKEN_TIMEOUT = 300

DEB_UPLOAD_PATH = os.path.join(basedir, "deb")

CELERY_BROKER_URL = "amqp://imods:imodsmq@localhost/imods"
# pickle is not safe, json takes more memory but should be ok if we don't pass
# large objects to tasks
CELERY_ACCEPT_CONTENT = ['json', 'msgpack', 'yaml']
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = 'json'

SECRET_KEY = 'somescretkey'  # Replace this in production

SQLITE_DB_PATH = os.path.join(basedir, 'imods.db')

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + SQLITE_DB_PATH
DATABASE_CONNECT_OPTIONS = {}

CSRF_ENABLED = True
CSRF_SESSION_KEY = "somethingimpossibletoguess"

BOTO_PROFILE = 'imods_testing'

STRIPE_API_KEY = "sk_test_THSmIZgT2oLYqX56g3VeGOBd"
S3_ASSETS_BUCKET = 'imods'
S3_PKG_BUCKET = 'imods_package'
S3_MEDIA_BASE_PATH = 'static/media'

PKG_INDEX_FILE_NAME = "Packages.gz"

# Download links expires in 30 minutes
DOWNLOAD_URL_EXPIRES_IN = 30*60
