from imods import db

WishList = db.Table('WISHLIST',
                    db.Column('user_id', db.Integer, db.ForeignKey('USER.uid')),
                    db.Column('item_id', db.Integer, db.ForeignKey('ITEM.iid'))
                    )
