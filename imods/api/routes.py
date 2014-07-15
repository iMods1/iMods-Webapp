from flask import request, session, Blueprint, jsonify
from werkzeug import check_password_hash, generate_password_hash
from imods import db
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
from datetime import datetime


api_mod = Blueprint("api_mods", __name__, url_prefix="/api")
setup_api_exceptions(api_mod)


success_reponse = {'message': 'successful'}


@api_mod.route("/user/profile")
@require_login
def user_profile():
    user = User.query.get(session['user']['uid'])
    if not user:
        raise ResourceIDNotFound()
    return jsonify(user.get_public())


@api_mod.route("/user/register", methods=["POST"])
@require_json
def user_register():
    req = request.json
    found = User.query.filter_by(email=req["email"]).first()
    if found:
        raise UserAlreadRegistered()

    newuser = User(req["fullname"], req["email"],
                   generate_password_hash(req["password"]),
                   "privatekey", req["age"], "author_identifier")
    db.session.add(newuser)
    db.session.commit()
    return success_reponse


@api_mod.route("/user/login", methods=["POST"])
@require_json
def user_login():
    req = request.json
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
        return success_reponse
    raise UserCredentialsDontMatch()


@api_mod.route("/user/<int:uid>/update")
@require_login
@require_json
def user_update(uid):
    user = User.query.get(uid)
    req = request.json
    if not User:
        raise ResourceIDNotFound()
    with db_scoped_session() as se:
        se.query(user).update(req)
    return success_reponse


@api_mod.route("/device/add", methods=["POST"])
@require_login
@require_json
def register_device():
    req = request.json
    user = session['user']
    dev_name = req['device_name']
    dev_imei = req['imei']
    dev_udid = req['udid']
    dev_model = req['model']
    device = Device(user['uid'], dev_name, dev_imei, dev_udid, dev_model)
    with db_scoped_session() as se:
        se.add(device)
    return success_reponse


@api_mod.route("/device/list", defaults={"device_id": None})
@api_mod.route("/device/<int:device_id>")
@require_login
@require_json
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
        devices = Device.query.filter_by(uid=session['user']['uid']).first()
        return map(JSONSerialize.get_public, devices)


@api_mod.route("/category/list", defaults={"cid": None})
@api_mod.route("/category/<int:cid>")
@require_json
def category_list(cid):
    if cid:
        category = Category.query.get(cid).first()
        return category.get_public
    elif cid is None:
        # Return all categories
        categories = Category.query.all()
        result = {}
        for cat in categories:
            result[cat.cid] = cat
        return result


@api_mod.route("/category/add", methods=["POST"])
@require_privileges([UserRole.Admin, UserRole.SiteAdmin])
@require_login
def category_add():
    req = request.json
    cat_name = req['name']
    cat_parent_id = req.get('parent_id')
    cat_description = req.get('description', '')
    category = Category(cat_name, cat_description, parent_id=cat_parent_id)
    db.session.add(category)
    db.session.commit()


@api_mod.route("/category/<int:cid>/update")
@require_privileges([UserRole.Admin, UserRole.SiteAdmin])
@require_login
@require_json
def category_update(cid):
    req = request.json
    category = Category.query.get(cid).first()
    with db_scoped_session() as se:
        # FIXME: Validate req
        se.query(category).update(req)
    return success_reponse


@api_mod.route("/category/<int:cid>/delete")
@require_privileges([UserRole.Admin, UserRole.SiteAdmin])
@require_login
def category_delete(cid):
    category = Category.query.get(cid).first()
    if len(category.children) or len(category.items) != 0:
        raise CategoryNotEmpty()
    with db_scoped_session() as se:
        se.delete(category)
    return success_reponse


@api_mod.route("/billing/list", defaults={'bid': None})
@api_mod.route("/billing/<int:bid>")
@require_login
def billing_list(bid):
    if bid:
        billing = BillingInfo.query.get(bid).first()
        if not billing:
            raise ResourceIDNotFound()
        return billing.get_public()
    else:
        billings = BillingInfo.query.all()
        return map(JSONSerialize.get_public, billings)


@api_mod.route("/billing/add")
@require_login
@require_json
def billing_add():
    req = request.json
    uid = session['user']['uid']
    if req.get('cc_expr'):
        cc_expr = datetime.strptime("%d/%y", req['cc_expr'])
    else:
        cc_expr = None
    billing = BillingInfo(uid, req['address'], req['zipcode'], req['state'],
                          req['type'], req.get('cc_no'), req.get('cc_name'),
                          cc_expr)
    with db_scoped_session() as se:
        se.add(billing)
    return success_reponse


@api_mod.route("/billing/<int:bid>/update")
@require_login
@require_json
def billing_update(bid):
    req = request.json
    if req.get('bid'):
        # Ignore bid in json data
        del req['bid']
    uid = session['user']['uid']
    billing = BillingInfo.query.filter_by(bid=bid, uid=uid).first()
    if not billing:
        raise ResourceIDNotFound()
    with db_scoped_session() as se:
        # FIXME: Validate req
        se.query(billing).update(req)
    return success_reponse


@api_mod.route("/billing/<int:bid>/delete")
@require_login
@require_json
def billing_delete(bid):
    uid = session['user']['uid']
    billing = BillingInfo.query.filter_by(bid=bid, uid=uid).first()
    if not billing:
        raise ResourceIDNotFound()
    with db_scoped_session() as se:
        se.delete(billing)
    return success_reponse


@api_mod.route("/item/list", defaults={"iid": None})
@api_mod.route("/item/<int:iid>")
@require_json
def item_list(iid):
    if iid:
        item = Item.query.get(iid=iid)
        return item.get_public()
    else:
        items = Item.query.all()
        return map(JSONSerialize.get_public, items)


@api_mod.route("/item/add")
@require_login
@require_json
def item_add(iid):
    req = request.json
    author_id = session['user']['author_identifier']
    item = Item(req['pkg_name'],
                req['pkg_version'],
                req['display_name'],
                author_id=author_id,
                price=req.get('price'),
                summary=req.get('summary'),
                description=req.get('description'),
                dependencies=req.get('dependencies'))
    with db_scoped_session() as se:
        se.add(item)
    return success_reponse


@api_mod.route("/item/<int:iid>/update")
@require_login
@require_json
def item_update(iid):
    req = request.json
    item = Item.query.get(iid)
    if not item:
        raise ResourceIDNotFound()
    with db_scoped_session() as se:
        se.query(item).update(req)
    return success_reponse


@api_mod.route("/item/<int:iid>/delete")
@require_login
@require_json
def item_delete(iid):
    req = request.json
    author_id = session['user']['author_identifier']
    role = session['user']['role']
    item = Item.query.get(iid)
    if not item:
        raise ResourceIDNotFound()
    if role in [UserRole.SiteAdmin] or author_id == item.author_id:
        with db_scoped_session() as se:
            # FIXME: Validate req
            se.query(item).update(req)
    else:
        raise InsufficientPrivileges()


@api_mod.route("/order/add")
@require_login
@require_json
def order_new():
    req = request.json
    user = User.query.get(session['user']['uid'])
    billing = BillingInfo.query.get(req['billing_method_id'])
    item = Item.query.get(req['item_id'])
    if not item:
        raise ResourceIDNotFound()
    order = Order(user, item, billing, req['total_price'], total_charged=req['total_charged'])
    with db_scoped_session() as se:
        se.add(order)
    return success_reponse


@api_mod.route("/order/list", defaults={"oid": None})
@api_mod.route("/order/<int:oid>")
@require_login
@require_json
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
        orders = Order.query.filter_by(uid=uid)
        return map(JSONSerialize.get_public, orders)


@api_mod.route("/order/<int:oid>/update")
@require_login
@require_json
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
@require_json
def order_cancel(oid):
    order = Order.query.get(oid)
    if not order:
        raise ResourceIDNotFound()
    with db_scoped_session() as se:
        se.query(order).update({'status': OrderStatus.OrderCancelled})
    return success_reponse
