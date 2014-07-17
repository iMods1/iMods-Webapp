from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

# This is needed when testing by wercker CI, otherwise, 'config' object won't be
# found.
CONFIG_OBJECT = os.environ.get('IMODS_CONFIG')

if CONFIG_OBJECT is not None:
    app.config.from_object('imods.configs.%s' % CONFIG_OBJECT)
else:
    app.config.from_object('imods.configs.development')

db = SQLAlchemy(app)


def init_db():
    db.create_all()


def drop_db():
    db.drop_all()

from imods.api.routes import api_mod
app.register_blueprint(api_mod)
