"""
.. module:: routes
    :synopsis: Endpoints of user API

.. moduleauthor:: Ryan Feng <odayfans@gmail.com>

"""
from flask import request, session, Blueprint, json
from werkzeug import check_password_hash, generate_password_hash
from imods.models import User, Order, Item, Device, Category, BillingInfo
from imods.models import UserRole, OrderStatus
from imods.models.mixin import JSONSerialize
from imods.decorators import require_login, require_json
from imods.decorators import require_privileges
from imods.helpers import db_scoped_session
from imods.api.exceptions import setup_api_exceptions
from imods.api.exceptions import UserAlreadRegistered, UserCredentialsDontMatch
from imods.api.exceptions import ResourceIDNotFound, CategoryNotEmpty
from imods.api.exceptions import InsufficientPrivileges, OrderNotChangable
from imods.api.exceptions import CategorySelfParent, BadJSONData
from datetime import datetime
import os
import operator
import base64


api_mod = Blueprint("api_mods", __name__, url_prefix="/api")
setup_api_exceptions(api_mod)


success_response = {'message': 'successful'}  #: A success_response


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
        return user.get_public()
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
    if session['user'] is not None:
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
        author_identifier=req.get("author_identifier") or user.author_identifier,
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


@api_mod.route("/device/list", defaults={"device_id": None})
@api_mod.route("/device/<int:device_id>")
@require_login
@require_json(request=False)
def device_list(device_id):
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
    if device_id:
        device = Device.query\
            .filter_by(uid=session['user']['uid'], dev_id=device_id)\
            .first()
        if not device:
            raise ResourceIDNotFound()
        return device.get_public()
    elif device_id is None:
        # List all devices
        devices = Device.query.filter_by(uid=session['user']['uid']).all()
        get_public = operator.methodcaller('get_public')
        res = map(get_public, devices)
        return res


@api_mod.route("/category/list", defaults={"cid": None})
@api_mod.route("/category/<int:cid>")
@require_json(request=False)
def category_list(cid):
    """
    Get category information.

    *** Request ***

    :queryparam int cid: unique category ID number

    *** Response ***
    :jsonparam int cid: category id
    :jsonparam int parent_id: parent category id
    :jsonparam string name: name of the category
    :jsonparam string description: description of the category

    :resheader Content-Type: application/js
    :status 200: no error :py:obj:`.success_response`
    :status 404: :py:exc:`.ResourceIDNotFound`
    """
    if cid:
        category = Category.query.get(cid)
        if not category:
            raise ResourceIDNotFound
        return category.get_public()
    elif cid is None:
        # Return all categories
        categories = Category.query.all()
        result = {}
        for cat in categories:
            result[cat.cid] = cat
        return result


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
    """
    req = request.get_json()
    if type(req) is not dict:
        req = dict(json.loads(req))
    cat_name = req['name']
    cat_parent_id = req.get('parent_id')
    cat_description = req.get('description', '')
    with db_scoped_session() as se:
        category = Category(name=cat_name,
                            description=cat_description,
                            parent_id=cat_parent_id)
        se.add(category)
        se.commit()
        return category.get_public()


@api_mod.route("/category/<int:cid>/update", methods=["POST"])
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


@api_mod.route("/category/<int:cid>/delete")
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
        items = se.query(Item).filter_by(category_id=cid).first()
        if children or items:
            raise CategoryNotEmpty()
        se.delete(category)
        se.commit()
    return success_response


@api_mod.route("/billing/list", defaults={'bid': None})
@api_mod.route("/billing/<int:bid>")
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

    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    :status 403: :py:exc:`.UserNotLoggedIn`
    :status 404: :py:exc:`.ResourceIDNotFound`
    """
    if bid:
        billing = BillingInfo.query.get(bid)
        if not billing:
            raise ResourceIDNotFound()
        return billing.get_public()
    else:
        billings = BillingInfo.query.all()
        return map(JSONSerialize.get_public, billings)


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
        cc_expr = datetime.strptime(req['cc_expr'], '%d/%y')
    else:
        cc_expr = None
    billing = BillingInfo(uid=uid,
                          address=req['address'],
                          zipcode=req['zipcode'],
                          state=req['state'],
                          country=req['country'],
                          type_=req['type_'],
                          cc_no=req.get('cc_no'),
                          cc_name=req.get('cc_name'),
                          cc_expr=cc_expr)
    with db_scoped_session() as se:
        se.add(billing)
        se.commit()
        return billing.get_public()


@api_mod.route("/billing/<int:bid>/update", methods=["POST"])
@require_login
@require_json()
def billing_update(bid):
    """
    Update a billing method.

    *** Request ***

    :jsonparam string address: billing address
    :jsonparam int zipcode: zipcode
    :jsonparam string state: state
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
    if req.get('cc_expr'):
        req['cc_expr'] = datetime.strptime(req['cc_expr'], '%d/%y')
    uid = session['user']['uid']
    billing = BillingInfo.query.filter_by(bid=bid, uid=uid).first()
    if not billing:
        raise ResourceIDNotFound()
    with db_scoped_session() as se:
        # FIXME: Validate req
        se.query(BillingInfo).filter_by(bid=bid).update(req)
        se.commit()
    return success_response


@api_mod.route("/billing/<int:bid>/delete")
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


@api_mod.route("/item/list", defaults={"iid": None})
@api_mod.route("/item/<int:iid>")
@require_json(request=False)
def item_list(iid):
    """
    Get information of an item.

    *** Request ***

    :query int iid: item id

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
    if iid:
        item = Item.query.get(iid)
        if not item:
            raise ResourceIDNotFound
        return item.get_public()
    else:
        items = Item.query.all()
        return map(JSONSerialize.get_public, items)


@api_mod.route("/item/add", methods=["POST"])
@require_login
@require_json()
def item_add():
    """
    Add a new item.

    *** Request ***

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


@api_mod.route("/item/<int:iid>/update", methods=["POST"])
@require_login
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


@api_mod.route("/item/<int:iid>/delete")
@require_login
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
    except:
        raise
    with db_scoped_session() as se:
        se.add(order)
        se.commit()
        return order.get_public()


@api_mod.route("/order/list", defaults={"oid": None})
@api_mod.route("/order/<int:oid>")
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

    :resheader Content-Type: application/json
    :status 200: no error :py:obj:`.success_response`
    :status 403: :py:exc:`.UserNotLoggedIn`
    :status 405: :py:exc:`.InsufficientPrivileges`
    :status 404: :py:exc:`.ResourceIDNotFound`
    """
    uid = session['user']['uid']
    if oid:
        order = Order.query.get(oid)
        if not order:
            raise ResourceIDNotFound()
        if order.uid != uid:
            raise InsufficientPrivileges()
        return order.get_public()
    else:
        # List all orders of a user
        # TODO: Add paging
        orders = Order.query.filter_by(uid=uid).all()
        return map(JSONSerialize.get_public, orders)


@api_mod.route("/order/<int:oid>/update", methods=["POST"])
@require_login
@require_json()
def order_udpate(oid):
    """
    Update an uncomplete order. Notice: an complete order cannot be changed.

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


@api_mod.route("/order/<int:oid>/cancel")
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
