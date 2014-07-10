from flask import request, url_for, escape, Blueprint, g, session, jsonify
from imods import db
from imods.models.user import User


api_mod = Blueprint("api_mods", __name__, url_prefix="/api")


@api_mod.route("/user/profile/<int:uid>")
def user_profile(uid):
    user = User.query.get(uid == uid)
    return jsonify(user.get_public())
