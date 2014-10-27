from imods import db, app
from contextlib import contextmanager
from os import path
import os


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
