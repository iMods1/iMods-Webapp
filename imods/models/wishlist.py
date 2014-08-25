from imods import db

#WishList = db.Table('WISHLIST', db.metadata,
                    #db.Column('uid', db.Integer, db.ForeignKey('USER.uid')),
                    #db.Column('iid', db.Integer, db.ForeignKey('ITEM.iid'))
                    #)

class WishList(db.Model):
    __tablename__ = "WISHLIST"
    uid = db.Column(db.Integer, db.ForeignKey('USER.uid'), primary_key=True)
    iid = db.Column(db.Integer, db.ForeignKey('ITEM.iid'), primary_key=True)
    item = db.relationship("Item")
