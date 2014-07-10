from imods import db
from imods.models.device import Device
from imods.models.billing_info import BillingInfo
from imods.models.item import Item
from imods.models.order import Order


class User(db.Model):
    __tablename__ = 'USER'

    uid = db.Column(db.Integer, nullable=False, primary_key=True, autoincrement=True)
    email = db.Column(db.String(200), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    fullname = db.Column(db.String(200), nullable=False)
    age = db.Column(db.Integer, default=0, nullable=True)
    author_identifier = db.Column(db.String(100), nullable=True)
    # The key for various encryption use
    private_key = db.Column(db.String(), nullable=False)

    # One to many relationship, if the user is deleted, all devices
    # registered under the account are deleted as well
    devices = db.relationship(Device,
                              backref="devices",
                              cascade="all,delete-orphan")

    billing_methods = db.relationship(BillingInfo,
                                      backref="owner",
                                      cascade="all,delete-orphan")

    items = db.relationship(Item,
                            backref="author",
                            passive_deletes="all")

    orders = db.relationship(Order,
                             backref="user",
                             cascade="all,delete-orphan")

    def __init__(self, fullname, email, password, private_key=None,
                 age=None, author_identifier=None):
        self.fullname = fullname
        self.email = email
        self.password = password
        self.private_key = private_key

    def __repr__(self):
        return "<User %r(%r uid=%r)>" % (self.fullname, self.email, self.uid)