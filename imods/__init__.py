"""iMods server documentation
.. moduleauthor:: Ryan Feng <odayfans@gmail.com>
"""
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CsrfProtect
import os

app = Flask(__name__)
CsrfProtect(app)

# This is needed when testing by wercker CI, otherwise, 'config' object won't be
# found.
CONFIG_OBJECT = os.environ.get('IMODS_CONFIG') or 'imods.configs.development'
CONFIG_FILE = os.environ.get('IMODS_CONFIG_FILE')

if CONFIG_FILE is not None:
    app.config.from_pyfile(CONFIG_FILE)
else:
    app.config.from_object(CONFIG_OBJECT)


db = SQLAlchemy(app)


def init_db():
    # Only create db file in testing and production, when the file is not
    # created.
    if app.config["TESTING"] or \
            not os.path.isfile(app.config["SQLITE_DB_PATH"]):
        db.create_all()
    elif app.config["DEBUG"]:
        pass


def drop_db(db):
    db.drop_all()

from imods.api.routes import api_mod
from imods.admin.views import imods_admin
app.register_blueprint(api_mod)
imods_admin.init_app(app)

init_db()
