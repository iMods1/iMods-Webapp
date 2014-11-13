import os

CONFIG_NAME = "PRODUCTION"

# Abs path of current file
basedir = os.environ.get('IMODS_DB_DIR') or '/var/db/imods.wunderkind.us'

DEBUG = True

ADMINS = [
    {
        'email': 'imods@imods.com',
        'password': 'iModsAdmin123',
        'author_id': 'imodsadmin'
    }
]

DEFAULT_CATEGORIES = [
    {
        'name': 'featured',
        'description': 'featured apps',
    },
]

CACHE_CONFIG = {
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_HOST': '172.30.3.216',
    'CACHE_REDIS_PORT': '6379'
}

TOKEN_TIMEOUT = 300

UPLOAD_PATH = os.path.join(basedir, "deb")

CELERY_BROKER_URL = "amqp://imods:7ujm6yhn5tgb4rfv@localhost/imods"

SECRET_KEY = 'h\xcf\x08MW\x8d"\xde\xe5\xc1V\'\xa8(\x96\x910v\x14\x12#\xa1\x91K'

SQLITE_DB_PATH = os.path.join(basedir, 'imods.db')

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + SQLITE_DB_PATH
DATABASE_CONNECT_OPTIONS = {}

CSRF_ENABLED = True
CSRF_SESSION_KEY =\
    'h\xb8b,b\xb6g]L\x04\x06\xa7\xb1\xf7C`\xda\xa4\xfbQ~\xf9\x02\xc9'

BOTO_PROFILE = 'imods_production'

S3_ASSETS_BUCKET = 'imods'
S3_PKG_BUCKET = 'imods_package'

PKG_INDEX_FILE_NAME = "Packages.gz"

# Download links expires in 30 minutes
DOWNLOAD_URL_EXPIRES_IN = 30*60

STRIPE_API_KEY = "sk_test_THSmIZgT2oLYqX56g3VeGOBd"
