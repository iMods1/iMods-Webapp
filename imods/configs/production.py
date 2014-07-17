import os

# Abs path of current file
basedir = '/var/db/imods.wunderkind.us'

DEBUG = FALSE

ADMINS = frozenset(['odayfans@gmail.com'])
SECRET_KEY = 'h\xcf\x08MW\x8d"\xde\xe5\xc1V\'\xa8(\x96\x910v\x14\x12#\xa1\x91K'

SQLITE_DB_PATH = os.path.join(basedir, 'imods.db')
# Create db file
if not os.path.isfile(SQLITE_DB_PATH):
    from imods import init_db
    init_db()

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + SQLITE_DB_PATH
DATABASE_CONNECT_OPTIONS = {}

CSRF_ENABLED = True
CSRF_SESSION_KEY =\
    'h\xb8b,b\xb6g]L\x04\x06\xa7\xb1\xf7C`\xda\xa4\xfbQ~\xf9\x02\xc9'
