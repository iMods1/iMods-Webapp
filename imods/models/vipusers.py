from imods import db

class VIPUsers(db.Model):
    __tablename__ = "VIPUSERS"
    __public__ = ('vip_email')
    vip_email = db.Column(db.String(), primary_key=True, unique=True, nullable=False)
