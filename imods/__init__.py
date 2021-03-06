"""iMods server documentation
.. moduleauthor:: Ryan Feng
"""
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.cache import Cache
import paypalrestsdk
import boto
import os

app = Flask(__name__)

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


def init_folders():
    # Create upload folder if not exits
    if not os.path.exists(app.config["DEB_UPLOAD_PATH"]):
        try:
            os.makedirs(app.config["DEB_UPLOAD_PATH"])
        except:
            app.logger.warning("Failed to create deb upload folder %s,\
                               file uploading will not work.")


def init_cache():
    if not app.config.get('CACHE_CONFIG'):
        return
    if getattr(app, 'cache', None):
        return
    app.cache = Cache(app, config=app.config['CACHE_CONFIG'])


def init_s3():
    if os.environ.get('IMODS_TESTING'):
        return
    app.s3_conn = boto.connect_s3(profile_name=app.config["BOTO_PROFILE"])
    app.s3_assets_bucket = app.s3_conn.get_bucket(app.config["S3_ASSETS_BUCKET"])
    app.s3_pkg_bucket = app.s3_conn.get_bucket(app.config["S3_PKG_BUCKET"])


def init_paypal():
    if os.environ.get('IMODS_TESTING'):
        return
    app.paypal = paypalrestsdk.configure(app.config["PAYPAL_CONFIG"])


from imods.api.routes import api_mod
from imods.admin.views import imods_admin
app.register_blueprint(api_mod)
imods_admin.init_app(app)

init_db()
init_folders()
init_cache()
init_s3()
init_paypal()
