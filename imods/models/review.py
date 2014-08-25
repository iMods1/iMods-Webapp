from imods import db
from .mixin import JSONSerialize
from datetime import datetime


class Review(db.Model, JSONSerialize):
    __tablename__ = "REVIEW"
    __public__ = ("rid", "uid", "iid", "title", "content", "rating", "add_date",
                  "user.fullname", "item.display_name")

    rid = db.Column(db.Integer, primary_key=True, nullable=False,
                    autoincrement=True)
    uid = db.Column(db.Integer, db.ForeignKey("USER.uid"))
    iid = db.Column(db.Integer, db.ForeignKey("ITEM.iid"))
    rating = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(50), nullable=False)
    content = db.Column(db.String(500), nullable=False)
    add_date = db.Column(db.DateTime, nullable=False,
                         default=datetime.utcnow)
    user = db.relationship("User", back_populates="reviews")
    item = db.relationship("Item", back_populates="reviews")

    def __repr__(self):
        return "<Review of item '%r' rating %r>" % (self.item.pkg_name,
                                                    self.rating)
