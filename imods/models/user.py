from imods import app
from imods import db
from imods.helpers import db_scoped_session
from imods.models.device import Device
from imods.models.billing_info import BillingInfo
from imods.models.item import Item
from imods.models.order import Order
from imods.models.mixin import JSONSerialize
from imods.models.constants import UserRole, AccountStatus
from imods.models.wishlist import WishList
from imods.models.review import Review
import stripe


class User(db.Model, JSONSerialize):
    __tablename__ = 'USER'
    __public__ = ("uid", "email", "fullname", "age", "role",
                  "author_identifier")

    uid = db.Column(db.Integer, nullable=False,
                    primary_key=True, autoincrement=True)
    email = db.Column(db.String(200), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    fullname = db.Column(db.String(200), nullable=False)
    age = db.Column(db.Integer, default=0, nullable=True)
    author_identifier = db.Column(db.String(100), nullable=True)
    # Account status,e.g. registered, activated, suspended etc
    status = db.Column(db.Integer, nullable=False,
                       default=AccountStatus.PendingConfirmation)
    # The key for various encryption use
    # Account role/group for privilege checking
    role = db.Column(db.Integer, default=UserRole.User, nullable=False)
    private_key = db.Column(db.String(), nullable=False)

    # The Stripe customer token for this user object
    stripe_customer_token = db.Column(db.String(100), nullable=True)

    # One to many relationship, if the user is deleted, all devices
    # registered under the account are deleted as well
    devices = db.relationship(Device,
                              backref="owner",
                              cascade="all,delete-orphan")

    billing_methods = db.relationship(BillingInfo,
                                      lazy="dynamic",
                                      backref="owner",
                                      cascade="all,delete-orphan")

    items = db.relationship(Item,
                            backref="author",
                            passive_deletes="all")

    orders = db.relationship(Order,
                             lazy="dynamic",
                             backref="user",
                             cascade="all,delete-orphan")

    wishlist = db.relationship("WishList", lazy='dynamic')

    reviews = db.relationship(Review, back_populates="user")

    def __repr__(self):
        return "<User %r(%r uid=%r)>" % (self.fullname, self.email, self.uid)

    def get_or_create_stripe_customer_obj(self):
        stripe.api_key = app.config.get("STRIPE_API_KEY")
        try:
            return stripe.Customer.retrieve(self.stripe_customer_token)
        except Exception as e:
            # Stripe customer not found, create new customer
            stripe_customer_token = stripe.Customer.create(
                    description=self.fullname,
                    email=self.email
            )

            with db_scoped_session() as se:
                se.query(User).filter_by(uid=self.uid).update({"stripe_customer_token":stripe_customer_token.id})
                se.commit()

            return stripe_customer_token
