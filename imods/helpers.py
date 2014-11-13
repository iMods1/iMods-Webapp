from imods import db, app
from werkzeug.security import generate_password_hash
from contextlib import contextmanager
from os import path
import base64
import time
import re
import os


supported_code_injectors = {
    'mobilesubstrate': '^/?Library/MobileSubstrate/DynamicLibraries/.*\.dylib$'
}


@contextmanager
def db_scoped_session():
    session = db.create_scoped_session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


def generate_bucket_key(path, new_name, old_filename):
    _, ext = os.path.splitext(old_filename)
    filename = new_name + ext
    return os.path.join(path, filename)


def detect_tweak(filelist):
    reg_list = []
    for _, pat in supported_code_injectors.iteritems():
        r = re.compile(pat)
        reg_list.append(r)

    for filepath in filelist:
        for reg in reg_list:
            if reg.match(filepath):
                return filepath

    return None


def get_pkg_paths(pkg_name, pkg_ver):
    pkg_fullname = pkg_name + '-' + str(pkg_ver)
    assets_base_path = path.join("packages", pkg_name, pkg_fullname, 'assets')
    pkg_root_path = path.join("packages", pkg_name)

    # Deb path
    pkg_s3_key_path = path.join(pkg_root_path, pkg_fullname+'.deb')

    pkg_local_cache_path = path.join(
        app.config["UPLOAD_PATH"],
        pkg_s3_key_path)

    pkg_local_cache_dir = path.dirname(pkg_local_cache_path)

    # Assets paths
    icon_base_path = path.join(assets_base_path, "icons")
    ss_base_path = path.join(assets_base_path, "screenshots")

    return {
        'pkg_fullname': pkg_fullname,
        'pkg_root_path': pkg_root_path,
        'pkg_local_cache_path': pkg_local_cache_path,
        'pkg_local_cache_dir': pkg_local_cache_dir,
        'pkg_s3_key_path': pkg_s3_key_path,
        'assets_base_path': assets_base_path,
        'icon_base_path': icon_base_path,
        'ss_base_path': ss_base_path
    }


# Generate a one-time token used by a variety of functions
def generate_onetime_token(key, prefix='', timeout=None):
    cache_key = path.join('token', prefix, key)
    res = app.cache.get(cache_key)
    if res:
        return res
    raw = generate_password_hash(key+str(time.time()))
    res = base64.urlsafe_b64encode(raw)
    app.cache.set(cache_key,
                  res,
                  timeout or app.config.get('TOKEN_TIMEOUT') or 300)
    return res


def check_onetime_token(key, token, prefix=''):
    cache_key = path.join('token', prefix, key)
    tk = app.cache.get(cache_key)
    res = tk and tk == token
    app.cache.delete(cache_key)
    return res
