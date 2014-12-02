from flask import request, session, Blueprint, json, render_template
from flask import url_for, abort
from werkzeug import check_password_hash, generate_password_hash
from imods import app, db
from imods.models.constants import BillingType, AccountStatus
from imods.models import User, Order, Item, Device, Category, BillingInfo
from imods.models import UserRole, OrderStatus, Review, WishList, Banner
from imods.decorators import require_login, require_json
from imods.decorators import require_privileges
from imods.helpers import db_scoped_session, generate_onetime_token
from imods.helpers import generate_bucket_key, check_onetime_token
from imods.tasks.dpkg import upload_to_s3
from imods.api.exceptions import *
from datetime import datetime
from tempfile import mkstemp
import boto
import boto.ses
import os
import operator
import urllib
import urlparse


api_mod = Blueprint("api_mods", __name__, url_prefix="/api")
setup_api_exceptions(api_mod)


success_response = {'status_code': 200, 'message': 'successful'}
#: A success_response


DEFAULT_LIMIT = 5
MAX_LIMIT = 100
MIN_REVIEW_CONTENT_LEN = 10
MIN_REVIEW_TITLE_LEN = 4


@api_mod.route("/user/profile")
@require_login
@require_json(request=False)
def user_profile():
    """
    Get user profile.

    *** Response ***

    :jsonparam int uid: user's unique id
    :jsonparam string fullname: full name of the user
    :jsonparam string email: email address of the user
    :jsonparam int age: age of the user, used for content access
    :jsonparam string author_identifier: identifier string for content authors

    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    :status 404: :py:exc:`.ResourceIDNotFound`
    :status 403: :py:exc:`.UserNotLoggedIn`
    """
    user = User.query.get(session['user']['uid'])
    if not user:
        raise ResourceIDNotFound()
    return user.get_public()


@api_mod.route("/user/profile_image")
@require_login
@require_json(request=False)
def user_profile_image():
    """
    Get or set user profile image.

    *** Request ***
    :param binary image_file: image data

    *** Response ***
    :jsonparam string profile_image_url: the url of user's profile image

    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    :status 404: :py:exc:`.ResourceIDNotFound`
    :status 403: :py:exc:`.UserNotLoggedIn`
    """
    user = User.query.get(session['user']['uid'])
    if not user:
        raise ResourceIDNotFound()
    expire = app.config["DOWNLOAD_URL_EXPIRES_IN"]
    s3_key = app.s3_assets_bucket.get_key(user.profile_image_s3_keypath)
    if s3_key:
        url = s3_key.generate_url(expire)
    else:
        url = None
    res = dict(profile_image_url=url)
    return res


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]


@api_mod.route("/user/profile_image/upload", methods=["POST"])
@require_login
@require_json(request=False)
def user_profile_image_upload():
    """
    Upload user's profile image, any existing one will be replaced.

    *** Request ***

    *** Response ***
    :py:obj:`.success_response` if succeeded

    :reqheader Content-Type: multipart/form-data
    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    :status 404: :py:exc:`.ResourceIDNotFound`
    :status 403: :py:exc:`.UserNotLoggedIn`
    """
    user = User.query.get(session['user']['uid'])
    if not user:
        raise ResourceIDNotFound()
    imgfile = request.files.get("file")
    if not imgfile:
        raise BadFormData

    if not allowed_file(imgfile.filename):
        raise BadExtension

    _, tmpfile = mkstemp()
    imgfile.save(tmpfile)

    s3_keypath = generate_bucket_key(app.config["S3_MEDIA_BASE_PATH"],
                                     "profile_img_%s" % str(user.uid),
                                     imgfile.filename)
    user.profile_image_s3_keypath = s3_keypath
    db.session.commit()
    upload_to_s3(app.config["S3_ASSETS_BUCKET"],
                 s3_keypath,
                 tmpfile,
                 True)
    return success_response


def send_confirmation_email(email):
    # TODO: Put email sending in background, e.g. using celery
    token = generate_onetime_token(email, 'user_register_email_confirm')
    link_url = url_for('.user_confirm',
                       _external=True,
                       email=email,
                       token=token)
    link_text = 'Confirm your email.'
    query = urllib.urlencode([('email', email),
                              ('token', token)])
    imods_link_url = urlparse.urlunsplit(['imods',
                                          'user',
                                          'confirm',
                                          query,
                                          ''])
    html_body = render_template('email/confirmation.html',
                                link_url=link_url,
                                imods_link_url=imods_link_url,
                                link_text=link_text)
    ses = boto.ses.connect_to_region("us-east-1",
                                     profile_name=app.config.get("BOTO_PROFILE")
                                     )
    ses.send_email("no-reply@imods.wunderkind.us",
                   "iMods Registration Confirmation",
                   html_body,
                   [email],
                   format='html')


def send_reset_password_email(email):
    token = generate_onetime_token(email, 'user_reset_password', 60*60*24)
    #query = urllib.urlencode([('email', email),
                              #('token', token)])
    #imods_link_url = urlparse.urlunsplit(['imods',
                                          #'user',
                                          #'reset_password',
                                          #query,
                                          #''])
    #imods_link_text = "Reset password"
    link_url = url_for(".user_reset_password_client",
                       _external=True,
                       email=email,
                       token=token)
    link_text = "Reset password"
    html_body = render_template('email/reset_password.html',
                                link_url=link_url,
                                link_text=link_text)
    ses = boto.ses.connect_to_region("us-east-1",
                                     profile_name=app.config.get("BOTO_PROFILE")
                                     )
    ses.send_email("no-reply@imods.wunderkind.us",
                   "iMods Reset Password",
                   html_body,
                   [email],
                   format='html')


def send_password_changed_email_notification(email):
    html_body = render_template('email/password_was_reset_notification.html')
    ses = boto.ses.connect_to_region("us-east-1",
                                     profile_name=app.config.get("BOTO_PROFILE")
                                     )
    ses.send_email("no-reply@imods.wunderkind.us",
                   "Your iMods password has been reset",
                   html_body,
                   [email],
                   format='html')


@api_mod.route("/user/send_confirmation", methods=["POST"])
@require_json()
def user_send_confirmation():
    """ Send a confirmation email. for development only!"""
    if app.config.get('CONFIG_NAME') != "DEVELOPMENT":
        abort(403)
    req = request.get_json()
    email = req.get('email')
    if email is None:
        raise BadJSONData

    with db_scoped_session() as se:
        user = se.query(User).filter_by(email=email).first()
        if not user:
            raise ResourceIDNotFound
    try:
        send_confirmation_email(req.get('email'))
    except:
        raise
    return success_response


@api_mod.route("/user/confirm")
def user_confirm():
    """
    Confirm user email address.

    *** Request ***

    :queryparam string email: email address of the user
    :queryparam string token: Access token

    *** Response ***

    :reqheader Content-Type: N/A
    :resheader Content-Type: text/html
    :status 200: no error :py:obj:`.success_response`
    :status 401: failed to validate email.
    """
    email = request.args.get('email')
    token = request.args.get('token')
    if check_onetime_token(email, token, 'user_register_email_confirm'):
        with db_scoped_session() as se:
            try:
                user = se.query(User).filter_by(email=email).first()
                if not user:
                    raise InternalException("User not found in database, but has been activated.")
                user.status = AccountStatus.Activated
                se.commit()
            except:
                se.rollback()
                raise
        return render_template('user/confirmation_succ.html')
    else:
        return render_template('user/confirmation_fail.html'), 401


@api_mod.route("/user/request_reset_password")
@require_json(request=False)
def user_request_password():
    """
    Send a reset password link to user's email address.

    *** Request ***
    :queryparam string email: User email

    *** Response ***

    :reqheader Content-Type: N/A
    :reqheader Content-Type: application/json
    :status 200: no erro :py:obj:`.success_response`
    :status 400: :py:exc:`.BadURLRequest`
    :status 404: :py:exc:`.ResourceIDNotFound`
    """
    email = request.args.get('email')
    # TODO: Add access token to limit the API usage
    if not email:
        raise BadURLRequest

    with db_scoped_session() as se:
        user = se.query(User).filter_by(email=email).first()
        if not user:
            raise ResourceIDNotFound

    try:
        send_reset_password_email(email)
    except:
        raise InternalException('Unable to send email.')

    return success_response


@api_mod.route("/user/reset_password_client")
def user_reset_password_client():
    """
    Handle URl requests from user's email, it redirects to the custom
    url since Gmail strips them all.

    *** Request ***
    :queryparam string email: user email
    :queryparam string token: access token

    *** Response ***

    :status 301: Redirect to custom url
    :status 404: Block desktop users
    """
    # Request from the client, use user-agent to detect whether it's
    # from iOS or desktop
    email = request.args.get("email").strip()
    token = request.args.get("token").strip()
    if len(email) == 0 or len(token) == 0:
        abort(404)
    return render_template("user/reset_password.html",
                           post_url=url_for(".user_reset_password"),
                            email=email,
                            token=token)
    #user_agent = request.headers.get('User-Agent')
    #if detect_ios_by_useragent(user_agent):
        # Redirct to custom url
        #email = request.args.get("email").strip()
        #token = request.args.get("token").strip()
        #if len(email) == 0 or len(token) == 0:
            #abort(404)
        #query = urllib.urlencode([('email', email),
                                #('token', token)])
        #imods_link_url = urlparse.urlunsplit(['imods',
                                            #'user',
                                            #'reset_password',
                                            #query,
                                            #''])
        #print 'redirct:', imods_link_url
        #return redirect(imods_link_url)
    # Block desktop users


@api_mod.route("/user/reset_password", methods=["POST"])
#@require_json()
def user_reset_password():
    """
    Reset user's password.

    *** Request ***
    :jsonparam string email: email address of the user
    :jsonparam string token: access token
    :jsonparam string new_password: new password

    *** Response ***

    :reqheader Content-Type: application/json
    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    :status 400: :py:exc:`.BadJSONData`
    :status 403: :py:exc:`.InvalidToken`
    :status 404: :py:exc:`.ResourceIDNotFound`
    """
    #req = request.get_json()
    req = request.form
    email = req.get('email')
    if not email:
        raise BadJSONData

    with db_scoped_session() as se:
        user = se.query(User).filter_by(email=email).first()
        if not user:
            raise ResourceIDNotFound

        # Not a request, reset the password with new password
        token = req.get('token')
        newpwd = req.get('new_password')

        if not (token and check_onetime_token(email, token, 'user_reset_password')):
            raise InvalidToken

        if not newpwd:
            raise BadJSONData

        try:
            user.password = generate_password_hash(newpwd)
            se.commit()
            send_password_changed_email_notification(email)
        except:
            se.rollback()
            raise

        return render_template("user/confirmation_succ.html")


@api_mod.route("/user/register", methods=["POST"])
@require_json()
def user_register():
    """
    Register a new user.

    *** Request ***

    :jsonparam string fullname: full name of the user
    :jsonparam string email: email address of the user
    :jsonparam string password: user password
    :jsonparam string author_identifier: identifier string for content authors
    :jsonparam int age: age of the user, used for content access

    *** Response ***

    :jsonparam int uid: user's unique id
    :jsonparam string fullname: full name of the user
    :jsonparam string email: email address of the user
    :jsonparam int age: age of the user, used for content access
    :jsonparam string author_identifier: identifier string for content authors

    :reqheader Content-Type: application/json
    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    :status 409: :py:exc:`.UserAlreadRegistered`
    """
    # TODO: Register device at user registeration
    req = request.get_json()
    if type(req) is not dict:
        req = dict(json.loads(req))
    found = User.query.filter_by(email=req["email"]).first()
    if found:
        raise UserAlreadRegistered()

    newuser = User(fullname=req["fullname"], email=req["email"],
                   password=generate_password_hash(req["password"]),
                   private_key="privatekey", age=req["age"],
                   author_identifier="author_identifier")
    with db_scoped_session() as se:
        try:
            se.add(newuser)
            se.commit()
        except:
            se.rollback()
        try:
            if not app.config.get('TESTING'):
                send_confirmation_email(req["email"])
        except:
            pass
        return newuser.get_public()


@api_mod.route("/user/login", methods=["POST"])
@require_json()
def user_login():
    """
    User login.

    *** Request ***

    :jsonparam string email: email address of the user
    :jsonparam string password: user password

    *** Response ***

    :reqheader Content-Type: application/json
    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    :status 401: :py:exc:`.UserCredentialsDontMatch`
    """
    # TODO: Check device and verify client.
    req = request.get_json()
    if type(req) is not dict:
        req = dict(json.loads(req))
    user = User.query.filter_by(email=req["email"]).first()
    if user and check_password_hash(user.password, req["password"]):
        user_dict = {'uid': user.uid,
                     'email': user.email,
                     'fullname': user.fullname,
                     'age': user.age,
                     'author_identifier': user.author_identifier,
                     'role': user.role,
                     'private_key': user.private_key}
        session['user'] = user_dict
        return success_response
    raise UserCredentialsDontMatch()


@api_mod.route("/user/logout")
@require_json(request=False)
def user_logout():
    """
    User logout.
    This always returns a 200 OK.

    *** Request ***

    *** Response ***

    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    """
    if session.get('user') is not None:
        del session['user']
    return success_response


@api_mod.route("/user/update", methods=["POST"])
@require_login
@require_json()
def user_update():
    """
    Update user's profile.

    *** Request ***

    :jsonparam string fullname: full name of the user
    :jsonparam int age: age of the user, used for content access
    :jsonparam string author_identifier: identifier string for content authors
    :jsonparam string old_password: only used when changing password
    :jsonparam string new_password: only used when changing password

    *** Response ***

    :reqheader Content-Type: application/json
    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    :status 404: :py:exc:`.ResourceIDNotFound`
    :status 401: :py:exc:`.UserCredentialsDontMatch`
    :status 400: :py:exc:`.BadJSONData`
    :status 403: :py:exc:`.UserNotLoggedIn`
    """
    uid = session['user']['uid']
    user = User.query.get(uid)
    req = request.get_json()
    if type(req) is not dict:
        req = dict(json.loads(req))
    if not User:
        raise ResourceIDNotFound

    if req.get('old_password') and req.get('new_password'):
        # Check old password
        if not check_password_hash(user.password, req['old_password']):
            raise UserCredentialsDontMatch
    elif req.get('old_password') or req.get('new_password'):
        # Request only contains 'new_password'
        raise BadJSONData

    pwd = generate_password_hash(req['new_password']) if\
        req.get('new_password') else user.password

    data = dict(
        fullname=req.get("fullname") or user.fullname,
        age=req.get("age") or user.age,
        author_identifier=req.get("author_identifier")
        or user.author_identifier,
        password=pwd
    )
    with db_scoped_session() as se:
        se.query(User).filter_by(uid=uid).update(data)
        se.commit()
    return success_response


@api_mod.route("/device/add", methods=["POST"])
@require_login
@require_json()
def device_add():
    """
    Add a new device. Each user can only add up to 5 devices.

    *** Request ***

    :jsonparam string device_name: the name of the device. e.g. Ryan's iPhone
    :jsonparam string imei: IMEI number of the device
    :jsonparam string udid: UDID number of the device
    :jsonparam string model: the model number of the device

    *** Response ***

    :jsonparam int dev_id: the unique ID number of the device
    :jsonparam int uid: user id of the ownder
    :jsonparam string device_name: the name of the device. e.g. Ryan's iPhone
    :jsonparam string imei: IMEI number of the device
    :jsonparam string udid: UDID number of the device
    :jsonparam string model: the model number of the device

    :reqheader Content-Type: application/json
    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    :status 403: :py:obj:`.UserNotLoggedIn`
    """
    # TODO: Limit the number of devices can be registered.
    req = request.get_json()
    if type(req) is not dict:
        req = dict(json.loads(req))
    user = session['user']
    dev_name = req['device_name']
    dev_imei = req['imei']
    dev_udid = req['udid']
    dev_model = req['model']
    device = Device(uid=user['uid'],
                    device_name=dev_name,
                    IMEI=dev_imei,
                    UDID=dev_udid,
                    model=dev_model)
    with db_scoped_session() as se:
        se.add(device)
        se.commit()
        return device.get_public()


@api_mod.route("/device/list")
@api_mod.route("/device/<int:device_id>")
@require_login
@require_json(request=False)
def device_list(device_id=None):
    """
    Get information of a device.

    *** Request ***

    :queryparam device_id: the unique ID number of the device.

    *** Response ***

    :jsonparam int dev_id: the unique ID number of the device
    :jsonparam int uid: user id of the ownder
    :jsonparam string device_name: the name of the device. e.g. Ryan's iPhone
    :jsonparam string imei: IMEI number of the device
    :jsonparam string udid: UDID number of the device
    :jsonparam string model: the model number of the device

    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    :status 403: :py:exc:`.UserNotLoggedIn`
    :status 404: :py:exc:`.ResourceIDNotFound`
    """
    if device_id is not None:
        device = Device.query\
            .filter_by(uid=session['user']['uid'], dev_id=device_id)\
            .first()
        if not device:
            raise ResourceIDNotFound
        return device.get_public()
    else:
        # List all devices
        page = request.args.get('page') or 0
        limit = request.args.get('limit') or DEFAULT_LIMIT
        if limit > MAX_LIMIT:
            limit = MAX_LIMIT
        devices = Device.query
        devices.limit(limit)
        devices.offset(page * limit)
        devices = devices.filter_by(uid=session['user']['uid']).all()
        get_public = operator.methodcaller('get_public')
        res = map(get_public, devices)
        return res


@api_mod.route("/category/list", defaults={"cid": None, "name": None})
@api_mod.route("/category/id/<int:cid>", defaults={"name": None})
@api_mod.route("/category/name/<name>", defaults={"cid": None})
@require_json(request=False)
def category_list(cid, name):
    """
    Get category information.

    *** Request ***

    :queryparam int cid: unique category ID number
    :queryparam str name: category name

    *** Response ***

    :jsonparam int cid: category id
    :jsonparam int parent_id: parent category id
    :jsonparam string name: name of the category
    :jsonparam string description: description of the category
    :jsonparam array items: list of items included in the category

    _NOTE: /category/name/<name> returns a list(array) of categories_

    :resheader Content-Type: application/js
    :status 200: no error :py:obj:`.success_response`
    :status 404: :py:exc:`.ResourceIDNotFound`
    """
    if cid is not None:
        category = Category.query.get(cid)
        if not category:
            raise ResourceIDNotFound
        return category.get_public()
    elif name is not None:
        with db_scoped_session() as ses:
            categories = ses.query(Category).filter_by(name=name).all()
            get_public = operator.methodcaller('get_public')
            return map(get_public, categories)
    else:
        # Return all categories
        limit = request.args.get('limit') or DEFAULT_LIMIT
        if limit > MAX_LIMIT:
            limit = MAX_LIMIT
        page = request.args.get('page') or 0
        categories = Category.query
        categories.limit(limit)
        categories.offset(limit*page)
        categories = categories.all()
        get_public = operator.methodcaller('get_public')
        return map(get_public, categories)


@api_mod.route("/category/featured")
@require_json(request=False)
def category_featured():
    """
    Get featured apps info.

    *** Request ***

    *** Response ***
    :jsonparam int cid: category id
    :jsonparam int parent_id: parent category id
    :jsonparam string name: name of the category
    :jsonparam string description: description of the category

    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`

    _This method should always return 200._
    """
    with db_scoped_session() as ses:
        # TODO: cache featured category id or object
        featured = ses.query(Category).filter_by(name='featured').all()
        if len(featured) != 1:
            raise InternalException("Featured category is not found or multiple\
 instances are found.")
        return featured[0].get_public()


@api_mod.route("/category/add", methods=["POST"])
@require_login
@require_privileges([UserRole.Admin, UserRole.SiteAdmin])
@require_json()
def category_add():
    """
    Add a new category. Requires admin privileges.

    *** Request ***

    :jsonparam string name: category name
    :jsonparam int parent_id: parent category's id
    :jsonparam string description: description

    :reqheader Content-Type: application/json
    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    :status 403: :py:exc:`.UserNotLoggedIn`
    :status 405: :py:exc:`.InsufficientPrivileges`
    :status 409: :py:exc:`.CategoryNameReserved`
    """
    req = request.get_json()
    if type(req) is not dict:
        req = dict(json.loads(req))
    cat_name = req['name']
    if cat_name.strip().lower() in Category.reservedNames:
        raise CategoryNameReserved
    cat_parent_id = req.get('parent_id')
    cat_description = req.get('description', '')
    with db_scoped_session() as se:
        category = Category(name=cat_name,
                            description=cat_description,
                            parent_id=cat_parent_id)
        se.add(category)
        se.commit()
        return category.get_public()


@api_mod.route("/category/update/<int:cid>", methods=["POST"])
@require_login
@require_privileges([UserRole.Admin, UserRole.SiteAdmin])
@require_json()
def category_update(cid):
    """
    Update a category. Requires admin privileges.

    *** Request ***

    :queryparam int cid: category id
    :jsonparam int parent_id: parent category's id, shouldn't be itself
    :jsonparam string name: name of the category
    :jsonparam string description: description of the category

    *** Response ***

    :reqheader Content-Type: application/json
    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    :status 403: :py:exc:`.UserNotLoggedIn`
    :status 405: :py:exc:`.InsufficientPrivileges`
    :status 409: :py:exc:`.CategorySelfParent`
    """
    req = request.get_json()
    if type(req) is not dict:
        req = dict(json.loads(req))
    if req.get("parent_id") and req["parent_id"] == cid:
        raise CategorySelfParent

    with db_scoped_session() as se:
        # FIXME: Validate req
        se.query(Category).filter_by(cid=cid).update(req)
        se.commit()
    return success_response


@api_mod.route("/category/delete/<int:cid>")
@require_login
@require_privileges([UserRole.Admin, UserRole.SiteAdmin])
@require_json(request=False)
def category_delete(cid):
    """
    Delete a category. The category to delete must be empty(no sub-categories or
    items.

    *** Request ***

    :param int cid: category id

    *** Response ***

    :reqheader Content-Type: application/js
    :resheader Content-Type: application/js
    :status 200: no error :py:obj:`.success_response`
    :status 403: :py:exc:`.UserNotLoggedIn`
    :status 405: :py:exc:`.InsufficientPrivileges`
    :status 409: :py:exc:`.CategoryNotEmpty`
    """
    with db_scoped_session() as se:
        category = se.query(Category).get(cid)
        children = se.query(Category).filter_by(parent_id=cid).first()
        if children:
            raise CategoryNotEmpty()
        se.delete(category)
        se.commit()
    return success_response


@api_mod.route("/billing/list", defaults={'bid': None})
@api_mod.route("/billing/id/<int:bid>")
@require_login
@require_json(request=False)
def billing_list(bid):
    """
    Get information of billing method `bid`.

    *** Request ***

    :queryparam int bid: billing method ID

    *** Response ***

    :jsonparam int bid: billing method id
    :jsonparam int uid: user id
    :jsonparam string address: billing address
    :jsonparam int zipcode: zipcode
    :jsonparam string state: state
    :jsonparam string country: country
    :jsonparam string type_: payment method type, see :py:class:`.BillingType`
    :jsonparam string cc_no: last 4 digits of credit card number
    :jsonparam string cc_name: name on credit card

    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    :status 403: :py:exc:`.UserNotLoggedIn`
    :status 404: :py:exc:`.ResourceIDNotFound`
    """
    uid = session['user']['uid']
    user = User.query.get(uid)
    if bid is not None:
        billing = BillingInfo.query.get(bid)
        if not billing:
            raise ResourceIDNotFound()
        return billing.get_public()
    else:
        limit = request.args.get("limit") or DEFAULT_LIMIT
        if limit > MAX_LIMIT:
            limit = MAX_LIMIT
        page = request.args.get("page") or 0
        billings = user.billing_methods
        billings.offset(page*limit)
        billings.limit(limit)
        billings = billings.all()
        get_public = operator.methodcaller('get_public')
        return map(get_public, billings)


@api_mod.route("/billing/add", methods=["POST"])
@require_login
@require_json()
def billing_add():
    """
    Add a new billing method.

    *** Request ***

    :jsonparam string address: billing address
    :jsonparam int zipcode: zipcode
    :jsonparam string state: state
    :jsonparam string city: city
    :jsonparam string country: country
    :jsonparam string type_: payment method type, see :py:class:`.BillingType`
    :jsonparam string cc_no: credit card number, `optional`
    :jsonparam string cc_name: name on the credit card, `optional`
    :jsonparam string cc_expr: expiration date of the credit card, `optional`

    `cc_expr` must be in 'mm/yy' format.

    *** Response ***

    :reqheader Content-Type: application/json
    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    :status 400: :py:exc:`.CardCreationFailed`
    :status 403: :py:exc:`.UserNotLoggedIn`
    """
    req = request.get_json()
    if type(req) is not dict:
        req = dict(json.loads(req))
    uid = session['user']['uid']
    if req.get('cc_expr'):
        cc_expr = datetime.strptime(req['cc_expr'], '%m/%y')
    else:
        cc_expr = None
    # TODO: Verify creditcard info before add it to database
    cc_cvv = req.get('cc_cvv')
    if cc_cvv:
        del req['cc_cvv']
    billing = BillingInfo(uid=uid,
                          address=req['address'],
                          zipcode=req['zipcode'],
                          state=req['state'],
                          city=req['city'],
                          country=req['country'],
                          type_=req['type_'],
                          cc_no=req.get('cc_no'),
                          cc_name=req.get('cc_name'),
                          cc_expr=cc_expr)
    with db_scoped_session() as se:
        se.add(billing)
        try:
            billing.get_or_create_stripe_card_obj(cc_cvv)
            se.commit()
        except Exception as e:
            se.rollback()
            raise CardCreationFailed(str(e))
        return billing.get_public()


@api_mod.route("/billing/update/<int:bid>", methods=["POST"])
@require_login
@require_json()
def billing_update(bid):
    """
    Update a billing method.

    *** Request ***

    :jsonparam string address: billing address
    :jsonparam int zipcode: zipcode
    :jsonparam string state: state
    :jsonparam string city: city
    :jsonparam string country: country
    :jsonparam string type_: payment method type
    :jsonparam string cc_no: credit card number, `optional`
    :jsonparam string cc_name: name on the credit card, `optional`
    :jsonparam string cc_expr: expiration date of the credit card, `optional`

    `cc_expr` must be in 'mm/yy' format.

    *** Response ***

    :reqheader Content-Type: application/json
    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    :status 403: :py:exc:`.UserNotLoggedIn`
    :status 404: :py:exc:`.ResourceIDNotFound`
    """
    req = request.get_json()
    if type(req) is not dict:
        req = dict(json.loads(req))
    if req.get('bid'):
        # Ignore bid in json data
        del req['bid']
    if req.get('uid'):
        # Ignore uid in json data
        del req['uid']
    if req.get('cc_expr'):
        req['cc_expr'] = datetime.strptime(req['cc_expr'], '%d/%y')
    # TODO: Verify creditcard info before add it to database
    cc_cvv = req.get('cc_cvv')
    if cc_cvv:
        del req['cc_cvv']
    uid = session['user']['uid']
    billing = BillingInfo.query.filter_by(bid=bid, uid=uid).first()
    if not billing:
        raise ResourceIDNotFound()
    with db_scoped_session() as se:
        # FIXME: Validate req
        se.query(BillingInfo).filter_by(bid=bid).update(req)
        se.commit()
    return success_response


@api_mod.route("/billing/delete/<int:bid>")
@require_login
@require_json(request=False)
def billing_delete(bid):
    """
    Delete a billing method.

    *** Request ***

    :query int bid: billing method id

    *** Response ***

    :resheader Content-Type: applicatioin/json
    :status 200: no error :py:obj:`.success_response`
    :status 403: :py:exc:`.UserNotLoggedIn`
    :status 404: :py:exc:`.ResourceIDNotFound`
    """
    uid = session['user']['uid']
    with db_scoped_session() as se:
        billing = se.query(BillingInfo).filter_by(bid=bid, uid=uid).first()
        if not billing:
            raise ResourceIDNotFound()
        se.delete(billing)
        se.commit()
    return success_response


@api_mod.route("/item/list", defaults={"iid": None,
                "pkg_name": None, "cat_names": None})
@api_mod.route("/item/id/<int:iid>", defaults={"pkg_name": None,
                                "cat_names": None})
@api_mod.route("/item/pkg/<pkg_name>", defaults={"iid": None, "cat_names": None})
@api_mod.route("/item/cat/<cat_names>", defaults={"iid": None, "pkg_name": None})
@require_json(request=False)
def item_list(iid, pkg_name, cat_names):
    """
    Get information of an item.

    *** Request ***

    :query int iid: item id
    :query str pkg_name: unique package name
    :query str cat_names: list packges in categories, category names are comma separated
    E.g. /api/item/cat/Tweaks,Featured will get items under 'Tweaks' OR 'Featured'

    *** Response ***

    :jsonparam int iid: item id
    :jsonparam int category_id: category id
    :jsonparam string author_id: author identifier(not user id)
    :jsonparam string pkg_name: package name
    :jsonparam string display_name: display name of the package
    :jsonparam string pkg_version: package version
    :jsonparam string pkg_assets_path: the url of preview assets
    :jsonparam string pkg_dependencies: package dependencies
    :jsonparam float price: item price
    :jsonparam string summary: item summary
    :jsonparam string description: item description
    :jsonparam string add_date: add date of package
    :jsonparam string last_update_date: last update date of the package

    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    :status 404: :py:exc:`.ResourceIDNotFound`
    """
    if iid is not None:
        item = Item.query.get(iid)
        if not item:
            raise ResourceIDNotFound
        return item.get_public()
    elif pkg_name is not None:
        item = Item.query.filter_by(pkg_name=pkg_name).first()
        if not item:
            raise ResourceIDNotFound
        return item.get_public()
    elif cat_names is not None:
        cat_names = cat_names.split(',')
        categories = Category.query.filter(Category.name.in_(cat_names)).all()
        if not categories or len(categories) < 1:
            raise ResourceIDNotFound
        result = set(categories[0].items.all())
        for i in xrange(1, len(categories)):
            result &= set(categories[i].items.all())
        get_public = operator.methodcaller('get_public')
        return map(get_public, result)
    else:
        limit = request.args.get("limit") or DEFAULT_LIMIT
        if limit > MAX_LIMIT:
            limit = MAX_LIMIT
        page = request.args.get("page") or 0
        items = Item.query
        items.offset(limit*page)
        items.limit(limit)
        items = items.all()
        get_public = operator.methodcaller('get_public')
        return map(get_public, items)


@api_mod.route("/item/add", methods=["POST"])
@require_login
@require_privileges([UserRole.AppDev])
@require_json()
def item_add():
    """
    Add a new item.

    *** Request ***

    :jsonparam string pkg_name: package name
    :jsonparam string display_name: display name of the package
    :jsonparam string pkg_version: package version
    :jsonparam string pkg_dependencies: package dependencies
    :jsonparam float price: item price
    :jsonparam string summary: item summary
    :jsonparam string description: item description

    *** Response ***

    :reqheader Content-Type: application/json
    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    :status 403: :py:exc:`.UserNotLoggedIn`
    :status 405: :py:exc:`.InsufficientPrivileges`
    """
    req = request.get_json()
    if type(req) is not dict:
        req = dict(json.loads(req))
    author_id = req.get("author_id") or session['user']['author_identifier']
    item = Item(pkg_name=req['pkg_name'],
                pkg_version=req['pkg_version'],
                display_name=req['display_name'],
                author_id=author_id,
                price=req.get('price'),
                summary=req.get('summary'),
                description=req.get('description'),
                pkg_dependencies=req.get('pkg_dependencies'))
    with db_scoped_session() as se:
        se.add(item)
        se.commit()
        return item.get_public()


@api_mod.route("/item/update/<int:iid>", methods=["POST"])
@require_login
@require_privileges([UserRole.AppDev])
@require_json()
def item_update(iid):
    """
    Update an item.

    *** Request ***

    :query iid: item id
    :jsonparam int category_id: category id
    :jsonparam string pkg_name: package name
    :jsonparam string display_name: display name of the package
    :jsonparam string pkg_version: package version
    :jsonparam string pkg_dependencies: package dependencies
    :jsonparam float price: item price
    :jsonparam string summary: item summary
    :jsonparam string description: item description

    *** Response ***

    :reqheader Content-Type: application/json
    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    :status 403: :py:exc:`.UserNotLoggedIn`
    :status 404: :py:exc:`.ResourceIDNotFound`
    :status 405: :py:exc:`.InsufficientPrivileges`
    """
    req = request.get_json()
    if type(req) is not dict:
        req = dict(json.loads(req))
    item = Item.query.get(iid)
    if not item:
        raise ResourceIDNotFound()
    with db_scoped_session() as se:
        se.query(Item).filter_by(iid=iid).update(req)
        se.commit()
    return success_response


@api_mod.route("/item/delete/<int:iid>")
@require_login
@require_privileges([UserRole.AppDev])
@require_json(request=False)
def item_delete(iid):
    """
    Delete an item.

    *** Request ***

    :query int iid: item id

    *** Response ***

    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    :status 403: :py:exc:`.UserNotLoggedIn`
    :status 404: :py:exc:`.ResourceIDNotFound`
    :status 405: :py:exc:`.InsufficientPrivileges`
    """
    author_id = session['user']['author_identifier']
    role = session['user']['role']
    with db_scoped_session() as se:
        item = se.query(Item).get(iid)
        if not item:
            raise ResourceIDNotFound()
        if role in [UserRole.SiteAdmin] or author_id == item.author_id:
            # FIXME: Validate req
            se.delete(item)
            se.commit()
        else:
            raise InsufficientPrivileges()
    return success_response


@api_mod.route("/item/featured")
@require_json(request=False)
def items_featured():
    with db_scoped_session() as ses:
        # TODO: cache featured category id or object
        featured = ses.query(Category).filter_by(name='featured').all()
        if len(featured) != 1:
            raise InternalException("Featured category is not found or multiple\
 instances are found.")
        get_public = operator.methodcaller('get_public')
        # TODO: cache featured items
        items = featured[0].items.all()
        return map(get_public, items)


@api_mod.route("/order/add", methods=["POST"])
@require_login
@require_json()
def order_add():
    """
    Place a new order.

    *** Request ***

    :jsonparam int billing_id: the id of billing method
    :jsonparam int item_id: item id
    :jsonparam int quantity: `optional`, default is 1
    :jsonparam string currency: `optional`, currency of the payment
    :jsonparam float total_price: total price of the items
    :jsonparam float total_charged: total charged, including tax and other fees

    *** Response ***

    :jsonparam int oid: order id
    :jsonparam int uid: user id
    :jsonparam string pkg_name: package name
    :jsonparam int quantity: quantity
    :jsonparam string currency: currency
    :jsonparam int status: order status, :py:class:`.OrderStatus`
    :jsonparam int billing_id: billing method id
    :jsonparam float total_price: total price
    :jsonparam float total_charged: total charged
    :jsonparam string order_date: the date of order placed
    :jsonparam dict billing: billing info
    :jsonparam dict item: item info

    :reqheader Content-Type: application/json
    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    :status 403: :py:exc:`.UserNotLoggedIn`
    :status 404: :py:exc:`.ResourceIDNotFound`
    :status 405: :py:exc:`.InsufficientPrivileges`
    """
    from imods import app
    import stripe
    stripe.api_key = app.config.get("STRIPE_API_KEY")
    req = request.get_json()
    if type(req) is not dict:
        req = dict(json.loads(req))
    uid = session['user']['uid']
    try:
        billing_id = req['billing_id']
        item_id = req['item_id']
    except KeyError:
        raise BadJSONData
    quantity = req.get("quantity") or 1
    currency = req.get("currency") or "USD"
    if quantity < 1:
        raise BadJSONData("Quantity cannot be less than 1.")
    item = Item.query.get(item_id)
    if not item:
        raise ResourceIDNotFound
    try:
        total_charge = quantity * item.price
        order = Order(uid=uid,
                      billing_id=billing_id,
                      pkg_name=item.pkg_name,
                      quantity=quantity, currency=currency,
                      total_price=total_charge,
                      total_charged=total_charge)
        # TODO: Calculate total and return back to client.
    except:
        raise
    with db_scoped_session() as se:
        try:
            billing_info = BillingInfo.query.get(billing_id)
            if billing_info and billing_info.type_ == BillingType.creditcard:
                user = User.query.get(uid)
                customer = user.get_or_create_stripe_customer_obj()
                if customer:
                    card = billing_info.get_or_create_stripe_card_obj(None)
                    stripe.Charge.create(
                        amount=int(quantity*item.price*100),
                        currency="usd",
                        customer=customer.id,
                        card=card.id,
                        description="imods order#{0}".format(order.oid)
                    )

            # Check whether if it's a free item
            if not billing_info and item.price > 0:
                raise InsufficientPrivileges("Need billing info for non-free items.")

            order.status = OrderStatus.OrderCompleted
        except:
            se.rollback()
            raise
        se.add(order)
        se.commit()
        return order.get_public()


@api_mod.route("/order/list", defaults={"oid": None})
@api_mod.route("/order/id/<int:oid>")
@require_login
@require_json(request=False)
def order_list(oid):
    """
    Get information of an order.

    *** Request ***

    :param int oid: order id

    *** Response ***


    :jsonparam int oid: order id
    :jsonparam int uid: user id
    :jsonparam string pkg_name: package name
    :jsonparam int quantity: quantity
    :jsonparam string currency: currency
    :jsonparam int status: order status, :py:class:`.OrderStatus`
    :jsonparam int billing_id: billing method id
    :jsonparam float total_price: total price
    :jsonparam float total_charged: total charged
    :jsonparam string order_date: the date of order placed
    :jsonparam dict billing: billing info
    :jsonparam dict item: item info

    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    :status 403: :py:exc:`.UserNotLoggedIn`
    :status 405: :py:exc:`.InsufficientPrivileges`
    :status 404: :py:exc:`.ResourceIDNotFound`
    """
    uid = session['user']['uid']
    if oid is not None:
        order = Order.query.get(oid)
        if not order:
            raise ResourceIDNotFound()
        if order.uid != uid:
            raise InsufficientPrivileges()
        return order.get_public()
    else:
        # List all orders of a user
        limit = request.args.get("limit") or DEFAULT_LIMIT
        if limit > MAX_LIMIT:
            limit = MAX_LIMIT
        page = request.args.get("page") or 0
        orders = Order.query
        orders.limit(limit)
        orders.offset(limit*page)
        orders = orders.filter_by(uid=uid).all()
        get_public = operator.methodcaller('get_public')
        return map(get_public, orders)

@api_mod.route("/order/user_item_purchases/<int:iid>")
@require_login
@require_json(request=False)
def order_user_item_purchases(iid):
    """
    Get information of all a user's orders by item id

    *** Request ***

    :param int iid: item id

    *** Response ***

    :jsonparam int oid: order id
    :jsonparam int uid: user id
    :jsonparam string pkg_name: package name
    :jsonparam int quantity: quantity
    :jsonparam string currency: currency
    :jsonparam int status: order status, :py:class:`.OrderStatus`
    :jsonparam int billing_id: billing method id
    :jsonparam float total_price: total price
    :jsonparam float total_charged: total charged
    :jsonparam string order_date: the date of order placed
    :jsonparam dict billing: billing info
    :jsonparam dict item: item info

    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    :status 403: :py:exc:`.UserNotLoggedIn`
    :status 405: :py:exc:`.InsufficientPrivileges`
    :status 404: :py:exc:`.ResourceIDNotFound`
    """

    uid = session['user']['uid']
    user = User.query.get(uid)
    orders = user.orders.filter_by(status=OrderStatus.OrderCompleted) \
            .filter(Order.item.has(iid=iid)).all()
    get_public = operator.methodcaller('get_public')
    return map(get_public, orders)

@api_mod.route("/order/stripe_purchase/<int:oid>", methods=["POST"])
@require_login
@require_json()
def order_stripe_purchase(oid):
    """
    Creates a new Stripe charge for the amount for the specified order

    *** Request ***

    :param int oid: order id
    :jsonparam string token: Stripe card token to charge

    *** Response ***

    :reqheader Content-Type: application/json
    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    :status 402: :py:exc:`.RequestFailed`
    :status 403: :py:exc:`.UserNotLoggedIn`
    :status 405: :py:exc:`.InsufficientPrivileges`
    :status 404: :py:exc:`.ResourceIDNotFound`
    """
    from imods import app
    import stripe

    uid = session['user']['uid']
    order = Order.query.get(oid)
    req = request.get_json()
    if not order:
        raise ResourceIDNotFound()
    if order.uid != uid:
        raise InsufficientPrivileges()
    stripe.api_key = app.config.get('STRIPE_API_KEY')

    total = int(order.total_price * 100) # Price in cents

    if total > 0:
        stripe.Charge.create( amount=total,
            currency=order.currency,
            card=req.get('token'),
            description="Charge for user: {0}, package: {1}, price: {2}".format(
                order.user.fullname,
                order.pkg_name, total)
        )

        print "Stripe charge successfully created"
    else:
        print "Total charge is:", total, " skipping stripe charge"

    with db_scoped_session() as se:
        se.query(Order).filter_by(oid=oid).update(
            {'status': OrderStatus.OrderCompleted}
        )
        se.commit()
    print "Order successfully updated"

    return success_response

@api_mod.route("/order/update/<int:oid>", methods=["POST"])
@require_login
@require_json()
def order_udpate(oid):
    """
    Update an uncomplete order. Notice: a complete order cannot be changed.

    *** Request ***

    :param int oid: order id
    :jsonparam int billing_id: the id of billing method
    :jsonparam int quantity: `optional`, default is 1
    :jsonparam string currency: `optional`, currency of the payment
    :jsonparam float total_price: total price of the items
    :jsonparam float total_charged: total charged, including tax and other fees

    *** Response ***

    :reqheader Content-Type: application/json
    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    :status 403: :py:exc:`.UserNotLoggedIn`
    :status 405: :py:exc:`.InsufficientPrivileges`
    :status 404: :py:exc:`.ResourceIDNotFound`
    :status 401: :py:exc:`.OrderNotChangable`
    """
    uid = session['user']['uid']
    order = Order.query.get(oid)
    req = request.get_json()
    if not order:
        raise ResourceIDNotFound
    if order.uid != uid:
        raise InsufficientPrivileges()
    if order.status != OrderStatus.OrderPlaced:
        raise OrderNotChangable()

    order.update(req)
    return success_response


@api_mod.route("/order/cancel/<int:oid>")
@require_login
@require_json(request=False)
def order_cancel(oid):
    """
    Cancel an order.

    *** Request ***

    :param int oid: order id

    *** Response ***


    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    :status 403: :py:exc:`.UserNotLoggedIn`
    :status 404: :py:exc:`.ResourceIDNotFound`
    :status 401: :py:exc:`.OrderNotChangable`
    """
    order = Order.query.get(oid)
    if not order:
        raise ResourceIDNotFound
    if order.status == OrderStatus.OrderCompleted:
        raise OrderNotChangable
    if not order:
        raise ResourceIDNotFound()
    with db_scoped_session() as se:
        se.query(Order).filter_by(oid=oid).update(
            {'status': OrderStatus.OrderCancelled}
        )
        se.commit()
    return success_response


@api_mod.route("/review/list", defaults={'uid': None, 'iid': None})
@api_mod.route("/review/user/<int:uid>", defaults={'iid': None})
@api_mod.route("/review/item/<int:iid>", defaults={'uid': None})
@require_json(request=False)
def review_list(uid, iid):
    """
    Query reviews by user or item.

    *** Request ***

    :reqheader Content-Type: application/json
    :param int uid: User ID
    :param int iid: item ID
    :queryparam int uid: User ID
    :queryparam int iid: Item ID

    Note:
    `/review/list?<int:uid>`
    is equivalent to
    `/review/user/<int:uid>`
    the same to item id

    *** Response ***

    :resheader Content-Type: application/json
    :jsonparam int uid: User ID
    :jsonparam int iid: Item ID
    :jsonparam int rating: Rating of the item.
    :jsonparam string content: The content of the review.

    :status 200: no error, returns a list of reviews in JSON.
    The list might be empty.
    """
    uid = uid or request.args.get('uid') or None
    iid = iid or request.args.get('uid') or None
    page = request.args.get("page") or 0
    limit = request.args.get("limit") or DEFAULT_LIMIT
    if limit > MAX_LIMIT:
        limit = MAX_LIMIT
    reviews = Review.query
    reviews.offset(limit * page)
    reviews.limit(limit)
    if uid:
        reviews = reviews.filter_by(uid=uid)
    if iid:
        reviews = reviews.filter_by(iid=iid)
    reviews = reviews.all()
    if len(reviews) < 1:
        return []
    get_public = operator.methodcaller('get_public')
    return map(get_public, reviews)


@api_mod.route("/review/add", methods=["POST"])
@require_login
@require_json()
def review_add():
    """
    Add a new review.

    *** Request ***

    :reqheader Content-Type: application/json
    :jsonparam int uid: User ID
    :jsonparam int iid: Item ID
    :jsonparam string title: Title of the review.\
        Must be at least :py:obj:`.MIN_REVIEW_TITLE_LEN` characters.
    :jsonparam string content: Content of the review,\
    must be at least :py:obj:`.MIN_REVIEW_CONTENT_LEN` characters.
    :jsonparam int rating: Rating of the item

    *** Response ***

    :resheader Content-Type: application/json
    :jsonparam int rid: The ID of the newly added review.
    :jsonparam int uid: User ID
    :jsonparam int iid: Item ID
    :jsonparam string content: Content of the review.
    :jsonparam int rating: Rating of the item.
    :jsonparam string add_date: date and time of the review was created

    :status 200: no error :py:obj:`.success_response`
    :status 403: :py:exc:`.UserNotLoggedIn`
    :status 400: :py:exc:`.BadJSONData`
    :status 404: :py:exc:`.ResourceIDNotFound` User or item is not found.
    """
    req = request.get_json()
    uid = session['user']['uid']
    iid = req.get('iid')
    title = req.get('title')
    content = req.get('content')
    rating = req.get('rating')
    if iid is None or content is None or rating is None or title is None:
        raise BadJSONData

    if User.query.get(uid) is None\
            or Item.query.get(iid) is None:
        raise ResourceIDNotFound

    if int(rating) < 0:
        raise BadJSONData("Rating must be a positive integer.")

    if len(content) < MIN_REVIEW_CONTENT_LEN:
        raise BadJSONData("Content must be at least %d characters"
                          % MIN_REVIEW_CONTENT_LEN)

    if len(title) < MIN_REVIEW_TITLE_LEN:
        raise BadJSONData("Title must be at least %d characters"
                          % MIN_REVIEW_TITLE_LEN)

    with db_scoped_session() as ses:
        review = Review(uid=uid, iid=iid, title=title,
                        content=content, rating=rating)
        ses.add(review)
        ses.commit()
        return review.get_public()


@api_mod.route("/review/update/<int:rid>", methods=["POST"])
@require_login
@require_json()
def review_edit(rid):
    """
    Edit a review.

    *** Request ***

    :reqheader Content-Type: application/json
    :param int rid: Review ID.
    :jsonparam string title: New title of the review.\
        Must be at least :py:obj:`.MIN_REVIEW_TITLE_LEN` characters.
    :jsonparam string content: New content of the review.\
        Must be at least :py:obj:`.MIN_REVIEW_CONTENT_LEN` characters.
    :jsonparam int rating: Rating of the item. Must be a positive integer.

    *** Response ***

    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    :status 400: :py:exc:`.BadJSONData`
    :status 403: :py:exc:`.UserNotLoggedIn`
    :status 404: :py:exc:`.ResourceIDNotFound`
    :status 405: :py:exc:`.InsufficientPrivileges`
    """
    req = request.get_json()
    with db_scoped_session() as ses:
        review = ses.query(Review).get(rid)
        if review is None:
            raise ResourceIDNotFound("Review not found")

        if review.uid != session['user']['uid']:
            raise InsufficientPrivileges

        title = req.get('title')
        content = req.get('content')
        rating = int(req.get('rating'))

        if title and len(title) < MIN_REVIEW_TITLE_LEN:
            raise BadJSONData("Title must be at least %d characters" %
                              MIN_REVIEW_TITLE_LEN)

        if content and len(content) < MIN_REVIEW_CONTENT_LEN:
            raise BadJSONData("Content must be at least %d characters" %
                              MIN_REVIEW_CONTENT_LEN)

        if rating is not None and rating < 0:
            raise BadJSONData("Rating must be a positive integer.")

        if title is not None:
            review.title = title

        if content is not None:
            review.content = content

        if rating is not None:
            review.rating = rating

        ses.commit()
        return success_response


@api_mod.route("/review/delete/<int:rid>")
@require_login
@require_json(request=False)
def review_delete(rid):
    """
    Delete a review.

    *** Request ***
    :param int rid: Review ID

    *** Response ***

    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    :status 403: :py:exc:`.UserNotLoggedIn`
    :status 404: :py:exc:`.ResourceIDNotFound`
    :status 405: :py:exc:`.InsufficientPrivileges`
    """
    with db_scoped_session() as ses:
        review = ses.query(Review).get(rid)
        if review is None:
            raise ResourceIDNotFound("Review ID not found")

        if review.uid != session['user']['uid']:
            raise InsufficientPrivileges

        ses.delete(review)
        ses.commit()
    return success_response


@api_mod.route("/wishlist")
@require_login
@require_json(request=False)
def wishtlist_list():
    """
    Get the wishlist of a user.

    *** Request ***

    *** Response ***

    :resheader Content-Type: application/json
    :jsonparam int iid: Item ID.

    :status 200: no error, returns a list of item IDs
    :status 403: :py:exc:`.UserNotLoggedIn`
    """
    with db_scoped_session() as ses:
        user = ses.query(User).get(session['user']['uid'])
        items = user.wishlist.all()
        return [wl.item.get_public() for wl in items]


@api_mod.route("/wishlist/add", methods=["POST"])
@require_login
@require_json()
def wishlist_add():
    """
    Add an item to wishlist.

    *** Request ***

    :reqheader Content-Type: application/json
    :jsonparam int iid: Item ID.

    *** Response ***

    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    :status 403: :py:exc:`.UserNotLoggedIn`
    :status 404: :py:exc:`.ResourceIDNotFound` Item not found.
    :status 405: :py:exc:`.BadJSONData`
    :status 409: :py:exc:`.ResourceUniqueError`
    """
    req = request.get_json()
    iid = req.get('iid')

    if iid is None:
        raise BadJSONData

    with db_scoped_session() as ses:
        item = ses.query(Item).get(iid)
        if item is None:
            raise ResourceIDNotFound("Item ID not found.")

        user = ses.query(User).get(session['user']['uid'])
        already_exists = ses.query(WishList)\
            .filter_by(uid=user.uid, iid=item.iid)\
            .first()
        if already_exists:
            raise ResourceUniqueError
        wishlist_item = WishList()
        wishlist_item.item = item
        user.wishlist.append(wishlist_item)
        ses.commit()
    return success_response


@api_mod.route("/wishlist/delete/<int:iid>")
@require_login
@require_json(request=False)
def wishlist_delete(iid):
    """
    Delete an item from the wishlist.

    *** Request ***

    :reqheader Content-Type: application/json
    :param int iid: Item ID.

    *** Response ***

    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    :status 403: :py:exc:`.UserNotLoggedIn`
    :status 404: :py:exc:`.ResourceIDNotFound`
    """
    with db_scoped_session() as ses:
        uid = session['user']['uid']
        wishlist_item = ses.query(WishList).filter_by(iid=iid, uid=uid).first()
        if wishlist_item is None:
            raise ResourceIDNotFound("Item not found in wishlist")

        ses.delete(wishlist_item)
        ses.commit()
    return success_response


@api_mod.route("/wishlist/clear")
@require_login
@require_json(request=False)
def wishlist_clear():
    """
    Delete all entries in wishlists.

    *** Request ***

    *** Response ***

    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    :status 403: :py:exc:`.UserNotLoggedIn`
    """
    with db_scoped_session() as ses:
        user = ses.query(User).get(session['user']['uid'])
        try:
            for wl in user.wishlist:
                ses.delete(wl)
            ses.commit()
        except Exception as e:
            ses.rollback()
            raise e
        # TODO: Add databse exception
        return success_response


@api_mod.route("/package/install", methods=["POST"])
@require_login
@require_json()
def package_install():
    """
    Calculates dependencies of a package and returns a list of packages need to
    be installed.

    *** Request ***

    :reqheader Content-Type: application/json
    :jsonparam array pkg_names: A list of names of the packages to be installed
    :jsonparam array installed_pkgs: A list of packages that already installed\
        on the client.
    :jsonparam str installed_pkgs[x].pkg_name: The name of an installed package
    :jsonparam str installed_pkgs[x].pkg_ver: The version of an installed package

    *** Response ***

    :resheader Content-Type: application/json
    :jsonparam array pkg_list: The calculated list of packages to be installed

    :status 200: no error :py:obj:`.success_response`
    :status 400: :py:exc:`.BadJSONData`
    :status 403: :py:exc:`.UserNotLoggedIn`
    :status 404: :py:exc:`.ResourceIDNotFound`
    """
    with db_scoped_session() as ses:
        req = request.json
        if req.get("pkg_names") is None:
            raise BadJSONData("`pkg_names` field not found.")
        if type(req["pkg_names"]) is not list:
            raise BadJSONData("`pkg_names` must be a list of package names.")

        target_pkgs = {}
        for pkg_name in req["pkg_names"]:
            pkg = ses.query(Item).filter_by(pkg_name=pkg_name).first()
            if pkg is None:
                raise ResourceIDNotFound()
            target_pkgs[pkg_name] = pkg

        # Build dependency graph
        class Pkg(object):
            def __init__(self, name, version):
                self.pkg_name = name
                self.pkg_version = version
                self.deps = []

            def compareVersion(self, pkg):
                pass


@api_mod.route("/package/index")
@require_login
@require_json(request=False)
def package_index():
    """
    Return download link to package index file.

    *** Request ***

    *** Response ***

    :resheader Content-Type: application/json
    :jsonparam string url: Download link to the package index file.
    :jsonparam int expires: Expiration time in seconds.

    :status 200: no error :py:obj:`.success_response`
    :status 403: :py:exc:`.UserNotLoggedIn`
    :status 404: :py:exc:`.ResourceIDNotFound` Package index doesn't exists.
    """
    s3 = boto.connect_s3(profile_name=app.config.get("BOTO_PROFILE"))
    bucket = s3.get_bucket(app.config["S3_PKG_BUCKET"])

    pkg_index = bucket.get_key(app.config["PKG_INDEX_FILE_NAME"])
    if pkg_index is None:
        raise ResourceIDNotFound("Index file not found.")

    expire = app.config["DOWNLOAD_URL_EXPIRES_IN"]

    url = pkg_index.generate_url(expires_in=expire)
    return {
            'url': url,
            'url_expires_in': expire
            }


# TODO: Move these reusable functions to a separate file
def get_item_assets(item, res_type):
    if item is None:
        return

    cached = app.cache.get("item/%d/assets/%s" % (item.iid, res_type))
    # Return cached data if available, note that "deb" type is an exception
    if cached and res_type != "deb":
        return cached

    # Connect to s3 buckets
    s3 = boto.connect_s3(profile_name=app.config.get("BOTO_PROFILE"))
    assets_bucket = s3.get_bucket(app.config["S3_ASSETS_BUCKET"])

    # Get paths
    assets_path = item.pkg_assets_path

    expire = app.config["DOWNLOAD_URL_EXPIRES_IN"]

    if res_type == "icons":
        # Get icons
        icons = []
        icons_path = os.path.join(assets_path, 'icons')
        icons_list = assets_bucket.list(icons_path)
        for icon in icons_list:
            if icon.name.endswith('/'):
                # Skip subfolders
                continue
            icon_url = icon.generate_url(expire)
            icon_name = os.path.basename(icon.name)
            icons.append(dict(name=icon_name, url=icon_url))

        result = icons


    if res_type == "screenshots":
        # Get screenshots
        screenshots = []
        screenshots_path = os.path.join(assets_path, 'screenshots')
        ss_list = assets_bucket.list(screenshots_path)
        for sshot in ss_list:
            if sshot.name.endswith('/'):
                continue
            sshot_url = sshot.generate_url(expire)
            sshot_name = os.path.basename(sshot.name)
            screenshots.append(dict(name=sshot_name, url=sshot_url))

        result = screenshots

    if res_type == "videos":
        # Get videos
        videos = []
        videos_path = os.path.join(assets_path, "videos")
        videos_list = assets_bucket.list(videos_path)
        for video in videos_list:
            if video.name.endswith('/'):
                continue
            video_name = os.path.basename(video.name)
            if video_name.startswith('youtube'):
                youtube_id = video_name.partition('-')[2]
            else:
                youtube_id = ""
            videos.append(dict(name=video_name, youtube_id=youtube_id, url=""))

        result = videos

    if res_type == "banners":
        # Get banner images
        banners = []
        banner_img_path = os.path.join(assets_path, "banners")
        banner_imgs = assets_bucket.list(banner_img_path)
        for banner in banner_imgs:
            if banner.name.endswith('/'):
                continue
            banner_img_filename = os.path.basename(banner.name)
            banner_img_url = banner.generate_url(expire)
            banners.append(dict(name=banner_img_filename, url=banner_img_url))

        result = banners

    if res_type == "deb":
        pkg_bucket = s3.get_bucket(app.config["S3_PKG_BUCKET"])
        deb_key = pkg_bucket.get_key(item.pkg_path)
        deb_url = deb_key.generate_url(expires_in=expire)
        deb = dict(deb_url=deb_url, deb_sha1_checksum=item.pkg_signature)
        result = deb

    if result is None:
        # assets type not found
        raise ResourceIDNotFound

    app.cache.set("item/%d/assets/%s" % (item.iid, res_type), result, expire)
    return result


@api_mod.route("/package/get", methods=["POST"])
@require_login
@require_json()
def package_get():
    """
    Get download links to package files(deb or assets).

    *** Request ***

    :reqheader Content-Type: application/json
    :jsonparam array item_ids: A list of item ids.
    :jsonparam array pkg_names: A list of package names.
    :jsonparam string type: "assets", "deb" or "all".

    NOTE: When `item_ids` and `pkg_names` are both present, only `item_ids` will be used.

    *** Response ***

    :resheader Content-Type: application/json
    :jsonparam array items: A list of items, each item is in the following structure.
    :jsonparam string item.item_id: Item id of the item
    :jsonparam string item.pkg_name: Package name of the item.
    :jsonparam string item.deb_url: Download url of the deb file.
    :jsonparam string item.deb_sha1_checksum: SHA1 checksum of the deb file
    :jsonparam int item.url_expires_in: Expiration time of `deb_url`, in seconds
    :jsonparam json item.assets: A json object contents assets urls.
    :jsonparam string item.assets.icons.url: URL of icon image.
    :jsonparam string item.assets.icons.name: Filename of icon image.
    :jsonparam string item.assets.screenshots.url: URL of item screenshot.
    :jsonparam string item.assets.screenshots.name: Filename of item screenshot.
    :jsonparam string item.assets.videos.name: video id name
    :jsonparam string item.assets.videos.youtueb_id: youtueb video id
    :jsonparam string item.assets.banners.name: banner image filename
    :jsonparam string item.assets.banners.url: url of banner images

    Example:
    [
    {
        "pkg_name":"a",
        "pkg_ver":"v1",
        "item_id":10,
        "deb_url":"https://imods.com/oajd0ajsd0ajsd0ajd0j",
        "url_expires_in":1800,
        "assets":{
            "icons":[
                {
                    "url":"https://imods.com/pkg/v1/icon.png",
                    "name":"icon.png"
                }
            ],
            "screenshots":[
                {
                    "url":"https://imods.com/pkg/v1/sshot1.png",
                    "name":"sshot1.png"
                }
            ],
            "videos": [
                {
                    "name": "youtube-WOIzQshmexc",
                    "youtube_id": "WOIzQshmexc"
                }
            ],
            "banners": [
                {
                    "name": "banner1.png",
                    "url": "https://imods.com/pkg/v1/banner.png"
                }
            ]
        }
    }
    ]

    :status 200: no error :py:obj:`.success_response`
    :status 400: :py:exec:`.BadJSONData`
    :status 403: :py:exec:`.UserNotLoggedIn`
    :status 404: :py:exec:`.ResourceIDNotFound` One or more items are not found.
    :status 405: :py:exec:`.InsufficientPrivileges` One or items are not available to the user, usually because the user didn't purchase them.
    """
    req = request.get_json()
    pkg_names = req.get('pkg_names')
    item_ids = req.get('item_ids')
    res_type = req.get('type')

    if res_type is None or (pkg_names is None and item_ids is None):
        raise BadJSONData

    if item_ids and type(item_ids) is not list:
        raise BadJSONData
    if pkg_names and type(pkg_names) is not list:
        raise BadJSONData

    if res_type not in ("assets", "deb", "all"):
        raise BadJSONData("Invalid type %s" % res_type)

    with db_scoped_session() as ses:
        items = []
        if item_ids:
            for iid in item_ids:
                item = ses.query(Item).get(iid)
                if not item:
                    raise ResourceIDNotFound("Item_id '%d' is not found" % iid)
                items.append(item)
        elif pkg_names:
            for name in pkg_names:
                item = ses.query(Item).filter_by(pkg_name=name).first()
                if not item:
                    raise ResourceIDNotFound("Package name '%s' is not found" % name)
                items.append(item)
        else:
            raise InternalException("This shouldn't happend")

        uid = session['user']['uid']
        user = ses.query(User).get(uid)
        if not user:
            raise InternalException(
                "User id %d is not found, but user is already logged in, probably a bug!" % uid)

        # Build order history
        # TODO: Use cache to speed up
        orders = {}
        for od in user.orders.all():
            orders[od.pkg_name] = True

        result = []

        # Verify user already purchased the item
        for item in items:
            # If the item is free, generate an order
            if res_type in ("deb", "all") and item.pkg_name not in orders:
                if abs(item.price) < 0.01:
                    with db_scoped_session() as se:
                        try:
                            total_charge = 1 * item.price * 100
                            order = Order(uid=uid,
                                          billing_id=None,
                                          pkg_name=item.pkg_name,
                                          quantity=1, currency='USD',
                                          total_price=total_charge,
                                          total_charged=total_charge)
                            se.add(order)
                            se.commit()
                            orders[item.pkg_name] = True
                        except:
                            se.rollback()
                            raise InternalException("Order cannot be added")
                else:
                    raise InsufficientPrivileges("Package '%s' need to be purchased before downloading"
                                                 % item.pkg_name)

            res_item = {
                'pkg_name': item.pkg_name,
                'pkg_ver': item.pkg_version,
                'deb_sha1_checksum': "",
                'deb_url': [],
                'url_expires_in': app.config["DOWNLOAD_URL_EXPIRES_IN"],
                'assets': {
                    'icons': get_item_assets(item, "icons"),
                    'screenshots': get_item_assets(item, "screenshots"),
                    'videos': get_item_assets(item, "videos"),
                    'banners': get_item_assets(item, "banners")
                }
            }

            if res_type in ("deb", "all"):
                item_deb = get_item_assets(item, "deb")
                res_item["deb_sha1_checksum"] = item_deb["deb_sha1_checksum"]
                res_item["deb_url"] = item_deb["deb_url"]

            result.append(res_item)

        return result


@api_mod.route("/banner/list")
@require_json(request=False)
def banner_list():
    """ Get all banner images and items information.

        *** Request ***
        :queryparam int item_id: item id of the banner item

        *** Response ***
        The response is a json array. Each element is a dictionary which contains banner information.
        :jsonparam int banner.banner_id: the indentifier of the banner image
        :jsonparam int banner.item_id: the identifier of the associated item of the banner image.
        :jsonparam dict banner.item: the item data. See `item_list`
        :jsonparam string banner.banner_imgs.name: image filename without extension.
        :jsonparam string banner.banner_imgs.url: url of the image

        :status 200: :py:obj:`.success_response`
        :status 404: :py:exc:`.ResourceIDNotFound`
        :status 500: :py:exc:`.InternalException`
    """
    item_id = request.args.get('item_id')
    with db_scoped_session() as ses:
        banners = []
        if item_id:
            item = ses.query(Item).get(item_id)
            if item is None:
                raise ResourceIDNotFound
            banners = [ses.query(Banner).filter(item_id == item_id)]
        else:
            banners = ses.query(Banner).all()

        result = []
        for banner in banners:
            banner_item = dict(banner_id=banner.banner_id,
                               item_id=banner.item_id,
                               item=banner.item.get_public(),
                               banner_imgs=get_item_assets(banner.item, "banners"))
            result.append(banner_item)
        return result
