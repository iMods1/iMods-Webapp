from imods import db
from imods.models.device import Device
from imods.models.billing_info import BillingInfo
from imods.models.item import Item
from imods.models.order import Order
from imods.models.mixin import JSONSerialize
from imods.models.constants import UserRole, AccountStatus
from imods.models.wishlist import WishList
from imods.models.review import Review


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
                       default=AccountStatus.Registered)
    # The key for various encryption use
    # Account role/group for privilege checking
    role = db.Column(db.Integer, default=UserRole.User, nullable=False)
    private_key = db.Column(db.String(), nullable=False)

    # One to many relationship, if the user is deleted, all devices
    # registered under the account are deleted as well
    devices = db.relationship(Device,
                              backref="owner",
                              cascade="all,delete-orphan")

    billing_methods = db.relationship(BillingInfo,
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
