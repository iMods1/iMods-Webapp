from imods import db
from constants import BillingType
from imods.models.mixin import JSONSerialize


class BillingInfo(db.Model, JSONSerialize):
    __tablename__ = "BILLING_INFO"
    __public__ = ("bid", "uid", "address", "zipcode", "state", "country", "type_")

    bid = db.Column(db.Integer, primary_key=True, nullable=False)
    uid = db.Column(db.Integer, db.ForeignKey('USER.uid'))
    address = db.Column(db.String(200), nullable=False)
    zipcode = db.Column(db.String(10), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    type_ = db.Column(db.String(200), default=BillingType.creditcard, nullable=False)
    credit_card_no = db.Column(db.String(100))
    credit_card_expr_date = db.Column(db.Date)
    credit_card_name = db.Column(db.String(200))

    def __init__(self, uid, address, zipcode, state, country,
                 type_=BillingType.creditcard,
                 credit_card_no=None, credit_card_name=None,
                 credit_card_expr_date=None):
        self.uid = uid
        self.type_ = type_
        self.address = address
        self.credit_card_no = credit_card_no
        self.credit_card_name = credit_card_name
        self.credit_card_expr_date = credit_card_expr_date

    def __repr__(self):
        # Don't print out any information other than billing type
        return "<Billing Type:%r>" % (self.type_)
