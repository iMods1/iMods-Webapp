from imods import db
from imods.models.mixin import JSONSerialize


association_table = db.Table('ITEM_CATEGORY_ASSOC',
    db.Column('category_id', db.Integer, db.ForeignKey('CATEGORY.cid')),
    db.Column('item_id', db.Integer, db.ForeignKey('ITEM.iid'))
)

class Category(db.Model, JSONSerialize):
    __tablename__ = "CATEGORY"
    __table_args = {"extend_existing": True}
    __public__ = ("cid", "parent_id", "name", "description", "items")

    reservedNames = ["featured"]

    cid = db.Column(db.Integer, primary_key=True, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("CATEGORY.cid"))
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(2000))

    children = db.relationship("Category",
                               backref=db.backref("parent", remote_side=[cid]),
                               )

    items = db.relationship("Item", secondary=association_table,
            backref=db.backref('categories', lazy='dynamic'), lazy='dynamic')

    def __repr__(self):
        return "<Category '%r'>" % (self.name)
