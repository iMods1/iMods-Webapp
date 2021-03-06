from imods import db
from imods.models.mixin import JSONSerialize
from datetime import datetime
from imods.models.review import Review
from sqlalchemy import text
# Removing 'import category' will cause table not found error
import category
# Remove PEP8 'not used' error
assert category is not None


class Item(db.Model, JSONSerialize):
    __tablename__ = "ITEM"
    __public__ = ("iid", "category_id", "author_id", "pkg_name",
                  "display_name", "pkg_version", "pkg_assets_path",
                  "price", "summary", "description",
                  "add_date", "last_update_date", "pkg_dependencies", "pkg_conflicts", "pkg_predepends", "type", "changelog")
    iid = db.Column(db.Integer, primary_key=True, nullable=False,
                    autoincrement=True)
    # author_id can be NULL because an item may be from a foreign source,
    # e.g. libc is standard c library and the author may not be present in
    # the database, so the author_id should be NULL
    # TODO: We may add a default author and assign all orhpan items to
    # that author
    author_id = db.Column(db.String(100),
                          db.ForeignKey("USER.author_identifier"), unique=True)
    pkg_name = db.Column(db.String(200), unique=True, nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    pkg_version = db.Column(db.String(100), nullable=False)
    pkg_signature = db.Column(db.String())
    pkg_path = db.Column(db.String())
    pkg_assets_path = db.Column(db.String())
    pkg_dependencies = db.Column(db.String())
    pkg_conflicts = db.Column(db.String())
    pkg_predepends = db.Column(db.String())
    price = db.Column(db.Float(), default=0.0, nullable=False)
    summary = db.Column(db.String(500))
    description = db.Column(db.String())
    changelog = db.Column(db.String())
    status = db.Column(db.Integer(), server_default=text('1'))
    type = db.Column(db.String())
    downloads = db.Column(db.Integer(), server_default=text('0'))
    # The content of the control file of a debian package
    control = db.Column(db.String())
    # Here we handle datetime at ORM level, because some databases don't handle
    # it well, and often cause problems.
    add_date = db.Column(db.Date(), default=datetime.utcnow, nullable=False)
    last_update_date = db.Column(db.Date(), default=datetime.utcnow,
                                 onupdate=datetime.utcnow, nullable=False)

    reviews = db.relationship(Review, back_populates="item",
                              cascade="all, delete-orphan")

    def dependencies(self):
        return "<Dependencies: %r>" % (self.pkg_dependencies)

    def __repr__(self):
        return "<Item '%r'-%r by %r>" % (self.pkg_name, self.pkg_version,
                                         self.author_id)

    def __hash__(self):
        return self.iid
