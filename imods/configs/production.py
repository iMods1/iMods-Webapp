import os

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

UPLOAD_PATH = "/tmp/imods"

SECRET_KEY = 'h\xcf\x08MW\x8d"\xde\xe5\xc1V\'\xa8(\x96\x910v\x14\x12#\xa1\x91K'

SQLITE_DB_PATH = os.path.join(basedir, 'imods.db')

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + SQLITE_DB_PATH
DATABASE_CONNECT_OPTIONS = {}

CSRF_ENABLED = True
CSRF_SESSION_KEY =\
    'h\xb8b,b\xb6g]L\x04\x06\xa7\xb1\xf7C`\xda\xa4\xfbQ~\xf9\x02\xc9'

BOTO_PROFILE = 'imods_production'

STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY')
