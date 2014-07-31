from imods import db
from contextlib import contextmanager


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
