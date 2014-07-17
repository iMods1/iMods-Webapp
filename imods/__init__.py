from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
import config

app = Flask(__name__)
app.config.from_object(config)

db = SQLAlchemy(app)


def init_db():
    db.create_all()


def drop_db():
    db.drop_all()

from imods.api.routes import api_mod
app.register_blueprint(api_mod)
