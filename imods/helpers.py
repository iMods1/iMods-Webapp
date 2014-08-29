from imods import db
from contextlib import contextmanager
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
    filename = ".".join([new_name, ext])
    return os.path.join(path, filename)

