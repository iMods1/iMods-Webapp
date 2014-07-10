from imods import db


class Category(db.Model):
    __tablename__ = "CATEGORY"
    __table_args = {"extend_existing": True}

    cid = db.Column(db.Integer, primary_key=True, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("CATEGORY.cid"))
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(2000))

    children = db.relationship("Category",
                               backref=db.backref("parents"),
                               remote_side=[cid],
                               lazy="joined",
                               join_depth=3)

    items = db.relationship("Item", backref="category", lazy="dynamic")

    def __init__(self, name, parent, description=None):
        self.name = name
        self.parent_id = parent.cid
        self.description = description or db.NULL

    def __repr__(self):
        return "<Category '%r'>" % (self.name)
