from imods import db
from imods.models.user import User
from flask import Blueprint, request, g, session, redirect, url_for
import json


user_mod = Blueprint('users', __name__, url_prefix="/user")


@user_mod.route('/')
def user_home():
    user = User("Ryan Feng", "odayfans@gmail.com", "hello")
    db.session.add(user)
    db.session.commit()
    return json.dump(user)
