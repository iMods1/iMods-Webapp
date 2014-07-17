from flask import request, session, Blueprint, json
from werkzeug import check_password_hash, generate_password_hash
from imods.models import User, Order, Item, Device, Category, BillingInfo
from imods.models import UserRole, OrderStatus
from imods.models.mixin import JSONSerialize
from imods.api.decorators import require_login, require_json
from imods.api.decorators import require_privileges
from imods.api.helpers import db_scoped_session
from imods.api.exceptions import setup_api_exceptions
from imods.api.exceptions import UserAlreadRegistered, UserCredentialsDontMatch
from imods.api.exceptions import ResourceIDNotFound, CategoryNotEmpty
from imods.api.exceptions import InsufficientPrivileges, OrderNotChangable
from imods.api.exceptions import CategorySelfParent
from datetime import datetime
import operator


api_mod = Blueprint("api_mods", __name__, url_prefix="/api")
setup_api_exceptions(api_mod)


success_response = {'message': 'successful'}


@api_mod.route("/user/profile")
@require_login
@require_json(request=False)
def user_profile():
    user = User.query.get(session['user']['uid'])
    if not user:
        raise ResourceIDNotFound()
    return user.get_public()


@api_mod.route("/user/register", methods=["POST"])
@require_json()
def user_register():
    # TODO: Register device at user registeration
    req = request.get_json()
    if type(req) is not dict:
        req = dict(json.loads(req))
    found = User.query.filter_by(email=req["email"]).first()
    if found:
        raise UserAlreadRegistered()

    newuser = User(req["fullname"], req["email"],
                   generate_password_hash(req["password"]),
                   "privatekey", req["age"], "author_identifier")
    with db_scoped_session() as se:
        se.add(newuser)
        se.commit()
        return newuser.get_public()


@api_mod.route("/user/login", methods=["POST"])
@require_json()
def user_login():
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
    if session['user'] is not None:
        del session['user']
    return success_response


@api_mod.route("/user/update", methods=["POST"])
@require_login
@require_json()
def user_update():
    uid = session['user']['uid']
    user = User.query.get(uid)
    req = request.get_json()
    if type(req) is not dict:
        req = dict(json.loads(req))
    if not User:
        raise ResourceIDNotFound
    if not check_password_hash(user.password, req['old_password']):
        raise UserCredentialsDontMatch
    data = dict(
        fullname=req["fullname"] or user.fullname,
        password=generate_password_hash(req['new_password'])
    )
    with db_scoped_session() as se:
        se.query(User).filter_by(uid=uid).update(data)
        se.commit()
    return success_response


@api_mod.route("/device/add", methods=["POST"])
@require_login
@require_json()
def device_add():
    # TODO: Limit the number of devices can be registered.
    req = request.get_json()
    if type(req) is not dict:
        req = dict(json.loads(req))
    user = session['user']
    dev_name = req['device_name']
    dev_imei = req['imei']
    dev_udid = req['udid']
    dev_model = req['model']
    device = Device(user['uid'], dev_name, dev_imei, dev_udid, dev_model)
    with db_scoped_session() as se:
        se.add(device)
        se.commit()
        return device.get_public()


@api_mod.route("/device/list", defaults={"device_id": None})
@api_mod.route("/device/<int:device_id>")
@require_login
@require_json(request=False)
def device_list(device_id):
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
    req = request.get_json()
    if type(req) is not dict:
        req = dict(json.loads(req))
    cat_name = req['name']
    cat_parent_id = req.get('parent_id')
    cat_description = req.get('description', '')
    with db_scoped_session() as se:
        category = Category(cat_name, cat_description, parent_id=cat_parent_id)
        se.add(category)
        se.commit()
        return category.get_public()


@api_mod.route("/category/<int:cid>/update", methods=["POST"])
@require_login
@require_privileges([UserRole.Admin, UserRole.SiteAdmin])
@require_json()
def category_update(cid):
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
    req = request.get_json()
    if type(req) is not dict:
        req = dict(json.loads(req))
    uid = session['user']['uid']
    if req.get('cc_expr'):
        cc_expr = datetime.strptime(req['cc_expr'], '%d/%y')
    else:
        cc_expr = None
    billing = BillingInfo(uid, req['address'], req['zipcode'], req['state'],
                          req['country'], req['type_'], req.get('cc_no'),
                          req.get('cc_name'),
                          cc_expr)
    with db_scoped_session() as se:
        se.add(billing)
        se.commit()
        return billing.get_public()


@api_mod.route("/billing/<int:bid>/update", methods=["POST"])
@require_login
@require_json()
def billing_update(bid):
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
    req = request.get_json()
    if type(req) is not dict:
        req = dict(json.loads(req))
    author_id = req.get("author_id") or session['user']['author_identifier']
    item = Item(req['pkg_name'],
                req['pkg_version'],
                req['display_name'],
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
    req = request.get_json()
    if type(req) is not dict:
        req = dict(json.loads(req))
    user = User.query.get(session['user']['uid'])
    billing = BillingInfo.query.get(req['billing_id'])
    item = Item.query.get(req['item_id'])
    quantity = req.get("quantity") or 1
    currency = req.get("currency") or "USD"
    if not item or not billing:
        raise ResourceIDNotFound()
    order = Order(user, item, billing, req['total_price'],
                  quantity=quantity, currency=currency,
                  total_charged=req['total_charged'])
    with db_scoped_session() as se:
        se.add(order)
        se.commit()
        return order.get_public()


@api_mod.route("/order/list", defaults={"oid": None})
@api_mod.route("/order/<int:oid>")
@require_login
@require_json(request=False)
def order_list(oid):
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
    uid = session['user']['uid']
    order = Order.query.get(oid)
    if not order:
        raise ResourceIDNotFound
    if order.uid != uid:
        raise InsufficientPrivileges()
    if order.status != OrderStatus.OrderPlaced:
        raise OrderNotChangable()


@api_mod.route("/order/<int:oid>/cancel")
@require_login
@require_json(request=False)
def order_cancel(oid):
    order = Order.query.get(oid)
    if not order:
        raise ResourceIDNotFound()
    with db_scoped_session() as se:
        se.query(Order).filter_by(oid=oid).update(
            {'status': OrderStatus.OrderCancelled}
        )
        se.commit()
    return success_response
