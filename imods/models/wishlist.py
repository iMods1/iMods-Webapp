from imods import db

WishList = db.Table('WISHLIST',
                    db.Column('uid', db.Integer, db.ForeignKey('USER.uid')),
                    db.Column('iid', db.Integer, db.ForeignKey('ITEM.iid'))
                    )
