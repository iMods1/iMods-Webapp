from flask import request, session, Blueprint, json
from werkzeug import check_password_hash, generate_password_hash
from imods.models import User, Order, Item, Device, Category, BillingInfo
from imods.models import UserRole, OrderStatus, Review, WishList
from imods.decorators import require_login, require_json
from imods.decorators import require_privileges
from imods.helpers import db_scoped_session
from imods.api.exceptions import setup_api_exceptions
from imods.api.exceptions import UserAlreadRegistered, UserCredentialsDontMatch
from imods.api.exceptions import ResourceIDNotFound, CategoryNotEmpty
from imods.api.exceptions import InsufficientPrivileges, OrderNotChangable
from imods.api.exceptions import CategorySelfParent, BadJSONData
from imods.api.exceptions import CategoryNameReserved, InternalException
from imods.api.exceptions import ResourceUniqueError
from datetime import datetime
import os
import operator
import base64


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
        se.add(newuser)
        se.commit()
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


@api_mod.route("/user/reset_password/<email>")
@require_json(request=False)
def user_reset_password(email):
    """
    Reset user's password. This will send an email with a new password to user.
    This always returns a 200 OK.

    *** Request ***

    :jsonparam email: user's email address

    *** Response ***
    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    """
    user = User.query.filter_by(email=email)
    if not user:
        return success_response
    newpwd = generate_password_hash(base64.b64decode(os.urandom(10)))
    user.password = newpwd
    # TODO: Send new password to user.
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
        se.commit()
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
                "pkg_name": None, "cat_name": None})
@api_mod.route("/item/id/<int:iid>", defaults={"pkg_name": None,
                                "cat_name": None})
@api_mod.route("/item/pkg/<pkg_name>", defaults={"iid": None, "cat_name": None})
@api_mod.route("/item/cat/<cat_name>", defaults={"iid": None, "pkg_name": None})
@require_json(request=False)
def item_list(iid, pkg_name, cat_name):
    """
    Get information of an item.

    *** Request ***

    :query int iid: item id
    :query str pkg_name: unique package name

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
    elif cat_name is not None:
        category = Category.query.filter_by(name=cat_name).first()
        if not category:
            raise ResourceIDNotFound
        get_public = operator.methodcaller('get_public')
        return map(get_public, category.items.all())
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
    :status 403: :py:exc:`.ResourceIDNotFound`
    """
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
    item = Item.query.get(item_id)
    if not item:
        raise ResourceIDNotFound
    try:
        order = Order(uid=uid,
                      billing_id=billing_id,
                      pkg_name=item.pkg_name,
                      quantity=quantity, currency=currency,
                      total_price=req['total_price'],
                      total_charged=req['total_charged'])
        # TODO: Calculate total and return back to client.
    except:
        raise
    with db_scoped_session() as se:
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

    stripe.Charge.create( amount=total,
        currency=order.currency,
        card=req.get('token'),
        description="Charge for user: {0}, package: {1}, price: {2}".format(
            order.user.fullname, 
            order.pkg_name, total)
    )

    print "Stripe charge successfully created"

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

    :status 200: no error: :py:obj:`.success_response`
    :status 404: :py:exc:`.ResourceIDNotFound`
    :status 405: :py:exc:`.BadJSONData`
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
        class Pkg(objcet):
            def __init__(self, name, version):
                self.pkg_name = name
                self.pkg_version = version
                self.deps = []

            def compareVersion(self, pkg):
                pass
