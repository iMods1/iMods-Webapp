from imods import db
from datetime import datetime


class Order(db.Model):
    __tablename__ = "ORDER"

    oid = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.Integer, db.ForeignKey("USER.uid", ondelete="CASCADE"))
    pkg_name = db.Column(db.String(200), db.ForeignKey("ITEM.package_name"))
    payment = db.Column(db.Integer, db.ForeignKey("BILLING_INFO.bid"))
    quantity = db.Column(db.Integer, default=1, nullable=False)
    currency = db.Column(db.String(3), default="USD", nullable=False)
    total_price = db.Column(db.Float)
    # If charged is NULL, then the order is not complete, user did't pay or the
    # payment failed
    charged = db.Column(db.Float, nullable=True)
    order_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __init__(self, user, item, billing, total_price, **kwargs):
        self.uid = user.uid
        self.pkg_name = item.package_name
        self.payment = billing.bid if billing else db.NULL
        self.quantity = kwargs.get("quantity", 1)
        self.currency = kwargs.get("currency", "USD")
        self.total_price = total_price or db.NULL
        self.charged = kwargs.get("charged", db.NULL)

    def __repr__(self):
        return "<Order: UserID '%r' Item '%r' Quantity %r Total %r>" %\
            (self.uid, self.pkg_name, self.quantity, self.total_price)
