from flask import *
from imods import db
from imods.models.user import User
from werkzeug import check_password_hash, generate_password_hash
from functools import wraps


api_mod = Blueprint("api_mods", __name__, url_prefix="/api")


@api_mod.route("/user/profile/<int:uid>")
def user_profile(uid):
    user = User.query.get(uid=uid)
    return jsonify(user.get_public())


def request_in_json(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not request.get_json(force=True, silent=True):
            return make_response("Invalid request data fromat", 400)
        return f(*args, **kwargs)
    return wrapper


@api_mod.route("/user/register", methods=["POST"])
@request_in_json
def user_register():
    req = request.json
    found = User.query.filter_by(email=req["email"]).first()
    if found:
        return make_response("User alreadly registered", 409)

    newuser = User(req["fullname"], req["email"], generate_password_hash(req["password"]),
                   "privatekey", req["age"], "author_identifier")
    db.session.add(newuser)
    db.session.commit()
    return make_response("", 200)


@api_mod.route("/user/login", methods=["POST"])
@request_in_json
def user_login():
    req = request.json
    user = User.query.filter_by(email=req["email"]).first()
    if user and check_password_hash(user.password, req["password"]):
        session['user_id'] = user.uid
        return make_response("Successfully logged in!", 200)
    return make_response("Invalid email and password combination.", 401)
