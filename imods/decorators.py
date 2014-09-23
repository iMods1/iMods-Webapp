from imods.api.exceptions import UserNotLoggedIn, BadJSONData
from imods.api.exceptions import InsufficientPrivileges
from functools import wraps
from flask import request, session, jsonify, make_response, json


def require_json(**kwargs):
    in_request = kwargs.get('request', True)
    in_response = kwargs.get('response', True)

    def dec(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if in_request and not request.get_json(force=True, silent=True):
                raise BadJSONData
            if in_response:
                r = f(*args, **kwargs)
                if type(r) is list:
                    res = make_response(json.dumps(r))
                    res.headers["Content-Type"] = "application/json"
                else:
                    res = jsonify(r)
                return res
            else:
                return f(*args, **kwargs)
        return wrapper
    return dec


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
