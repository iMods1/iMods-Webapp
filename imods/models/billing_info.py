from imods import db
from imods import app
from imods.helpers import db_scoped_session
import stripe
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
    cc_no = db.Column(db.String(100), nullable=True)
    cc_expr = db.Column(db.Date, nullable=True)
    cc_name = db.Column(db.String(200), nullable=True)
    stripe_card_token = db.Column(db.String(100), nullable=True)
    paypal_refresh_token = db.Column(db.String(), nullable=True)

    def __repr__(self):
        # Don't print out any information other than billing type
        return "<Billing Type:%r>" % (self.type_)

    def get_public(self, *args, **kwargs):
        result = super(BillingInfo, self).get_public(*args, **kwargs)
        if result.get('cc_no'):
            result['cc_no'] = self.cc_no[-4:]
        return result

    def get_or_create_stripe_card_obj(self, cvc=None):
        from imods.models import User
        stripe.api_key = app.config.get("STRIPE_API_KEY")
        user = User.query.get(self.uid)
        customer = user.get_or_create_stripe_customer_obj()
        try:
            return customer.cards.retrieve(self.stripe_card_token)
        except:
            stripe_card_token = customer.cards.create(
                card={
                        "number": self.cc_no,
                        "exp_month": self.cc_expr.month,
                        "exp_year": self.cc_expr.year,
                        "cvc": cvc
                    }
                )
            with db_scoped_session() as se:
                se.query(BillingInfo).filter_by(bid=self.bid).update({"stripe_card_token": stripe_card_token.id})
                se.commit()

            return stripe_card_token
