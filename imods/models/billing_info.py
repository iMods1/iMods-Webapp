from imods import db
from constants import BillingType


class BillingInfo(db.Model):
    __tablename__ = "BILLING_INFO"

    bid = db.Column(db.Integer, primary_key=True, nullable=False)
    uid = db.Column(db.Integer, db.ForeignKey('USER.uid'))
    address = db.Column(db.String(200), nullable=False)
    type_ = db.Column(db.String(200), default=BillingType.creditcard, nullable=False)
    credit_card_no = db.Column(db.String(100))
    credit_card_expr_date = db.Column(db.Date)
    credit_card_name = db.Column(db.String(200))

    def __init__(self, address, credit_card_no, credit_card_name,
                 credit_card_expr_date, type_=BillingType.creditcard):
        self.type_ = type_
        self.address = address
        self.credit_card_no = credit_card_no or db.NULL
        self.credit_card_name = credit_card_name or db.NULL
        self.credit_card_expr_date = credit_card_expr_date or db.NULL

    def __repr__(self):
        # Don't print out any information other than billing type
        return "<Billing Type:%r>" % (self.type_)
