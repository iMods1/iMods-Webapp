from imods import db
from datetime import datetime
from imods.models.mixin import JSONSerialize
from imods.models.billing_info import BillingInfo
from imods.models.constants import OrderStatus
from imods.models.item import Item


class Order(db.Model, JSONSerialize):
    __tablename__ = "ORDER"
    __public__ = ("oid", "uid", "pkg_name", "quantity", "currency", "status",
                  "billing_id", "total_price", "total_charged", "order_date",
                  "item", "billing")

    oid = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.Integer, db.ForeignKey("USER.uid", ondelete="CASCADE"))
    pkg_name = db.Column(db.String(200), db.ForeignKey("ITEM.pkg_name"))
    billing_id = db.Column(db.Integer, db.ForeignKey("BILLING_INFO.bid"))
    quantity = db.Column(db.Integer, default=1, nullable=False)
    currency = db.Column(db.String(3), default="USD", nullable=False)
    total_price = db.Column(db.Float)
    # If total_charged is NULL, then the order is not complete, user did't pay
    # or the payment failed
    status = db.Column(db.Integer, default=OrderStatus.OrderPlaced,
                       nullable=False)
    total_charged = db.Column(db.Float, nullable=True)
    order_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    item = db.relationship(Item)

    billing = db.relationship(BillingInfo)

    def __repr__(self):
        return "<Order: UserID '%r' Item '%r' Quantity %r Total %r>" %\
            (self.uid, self.pkg_name, self.quantity, self.total_price)
