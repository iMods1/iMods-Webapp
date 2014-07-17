import os

# Abs path of current file
basedir = os.path.abspath(os.path.dirname(__file__))

DEBUG = True

ADMINS = frozenset(['odayfans@gmail.com'])
SECRET_KEY = 'somescretkey'  # Replace this in production

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'imods.db')
DATABASE_CONNECT_OPTIONS = {}

CSRF_ENABLED = True
CSRF_SESSION_KEY = "somethingimpossibletoguess"
