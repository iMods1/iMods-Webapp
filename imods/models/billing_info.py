from imods import db
from constants import BillingType
from imods.models.mixin import JSONSerialize


class BillingInfo(db.Model, JSONSerialize):
    __tablename__ = "BILLING_INFO"
    __public__ = ("bid", "uid", "address", "zipcode", "city", "state",
                  "country", "type_")

    bid = db.Column(db.Integer, primary_key=True, nullable=False)
    uid = db.Column(db.Integer, db.ForeignKey('USER.uid'))
    address = db.Column(db.String(200), nullable=False)
    zipcode = db.Column(db.Integer, nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    type_ = db.Column(db.String(200), default=BillingType.creditcard,
                      nullable=False)
    cc_no = db.Column(db.String(100))
    cc_expr = db.Column(db.Date)
    cc_name = db.Column(db.String(200))

    def __repr__(self):
        # Don't print out any information other than billing type
        return "<Billing Type:%r>" % (self.type_)
