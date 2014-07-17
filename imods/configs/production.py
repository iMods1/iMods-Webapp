import os

# Abs path of current file
basedir = '/var/db/imods.wunderkind.us'

DEBUG = FALSE

ADMINS = frozenset(['odayfans@gmail.com'])
SECRET_KEY = 'h\xcf\x08MW\x8d"\xde\xe5\xc1V\'\xa8(\x96\x910v\x14\x12#\xa1\x91K'

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'imods.db')
DATABASE_CONNECT_OPTIONS = {}

CSRF_ENABLED = True
CSRF_SESSION_KEY =\
    'h\xb8b,b\xb6g]L\x04\x06\xa7\xb1\xf7C`\xda\xa4\xfbQ~\xf9\x02\xc9'
