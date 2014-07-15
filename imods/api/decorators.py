from imods.api.exceptions import UserNotLoggedIn, BadJSONData, InsufficientPrivileges
from functools import wraps
from flask import request, session, jsonify


def require_json(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not request.get_json(force=True, silent=True):
            raise BadJSONData()
        return jsonify(f(*args, **kwargs))
    return wrapper


def require_login(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('user'):
            raise UserNotLoggedIn()
        return f(*args, **kwargs)
    return wrapper


def require_privileges(priv_lst):
    def dec(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not session['user']['role'] in priv_lst:
                raise InsufficientPrivileges
            return f(*args, **kwargs)
        return wrapper
    return dec
