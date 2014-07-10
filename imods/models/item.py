from imods import db
from datetime import datetime
import category


class Item(db.Model):
    __tablename__ = "ITEM"
    # The primary key is the combination of the package name and the version,
    # because a package may have multiple versions and may be published by
    # different authors.
    # If an item is a derivative(fork) of the another item, then it should be named with a
    # new package name.
    __table_args__ = (db.PrimaryKeyConstraint("package_name", "package_version",
                                              name="package_id_PK"),)

    # ON DELETE CASCADE prevents the category from being deleted if it has at
    # least one item associated with it.
    category_id = db.Column(db.Integer,
                            db.ForeignKey("CATEGORY.cid", ondelete="CASCADE"))
    # author_id can be NULL because an item may be from a foreign source,
    # e.g. libc is standard c library and the author may not be present in
    # the database, so the author_id should be NULL
    # TODO: We may add a default author and assign all orhpan items to that author
    author_id            = db.Column(db.String(100),
                                     db.ForeignKey("USER.author_identifier"))
    package_name         = db.Column(db.String(200), nullable=False)
    display_name         = db.Column(db.String(100), nullable=False)
    package_version      = db.Column(db.String(100), nullable=False)
    package_signature    = db.Column(db.String())
    package_path         = db.Column(db.String())
    package_assets_path  = db.Column(db.String())
    package_dependencies = db.Column(db.String())
    price                = db.Column(db.Float())
    summary              = db.Column(db.String(500))
    description          = db.Column(db.String())
    # Here we handle datetime at ORM level, because some databases don't handle
    # it well, and often cause problems.
    add_date             = db.Column(db.Date(), default=datetime.utcnow, nullable=False)
    last_update_date     = db.Column(db.Date(), onupdate=datetime.utcnow, nullable=False)

    def __init__(self, pkg_name, pkg_version, display_name, **kwargs):
        author = kwargs.get('author', None)
        self.author_id = author.author_identifier if author else db.NULL
        self.package_name = pkg_name
        self.package_version = pkg_version
        self.display_name = display_name
        self.package_signature = kwargs.get('pkg_signature', db.NULL)
        self.package_path = kwargs.get('pkg_parth', db.NULL)
        self.package_assets_path = kwargs.get('pkg_preview_assets', db.NULL)
        self.summary = kwargs.get('summary', db.NULL)
        self.description = description or db.NULL
        self.dependencies = kwargs.get('dependencies', db.NULL)
        price = kwargs.get('price')
        if not price or price < 0.01:
            price = db.NULL
        self.price = price

    def dependencies(self):
        return "<Dependencies: %r>" % (self.package_dependencies)

    def __repr__(self):
        return "<Item '%r'-%r by %r>" % (self.package_name, self.package_version, self.author_id)
