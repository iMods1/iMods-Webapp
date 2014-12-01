from imods import app
from imods import db
from imods.models.mixin import JSONSerialize
from imods.models.item import Item

class Banner(db.Model, JSONSerialize):
    __tablename__ = 'BANNER'
    __public__ = ('banner_id', 'item', 'item_id', 'banner_assets_path')

    banner_id = db.Column(db.Integer, nullable=False, primary_key=True, autoincrement=True)
    item_id = db.Column(db.Integer, db.ForeignKey('ITEM.iid'), nullable=False)

    item = db.relationship(Item)
