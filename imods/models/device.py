from imods import db
from imods.models.mixin import JSONSerialize


class Device(db.Model, JSONSerialize):
    __tablename__ = "DEVICE"
    __public__ = ("dev_id", "uid", "device_name", "IMEI", "UDID", "model")

    dev_id = db.Column(db.Integer, nullable=False, primary_key=True)
    uid = db.Column(db.Integer, db.ForeignKey('USER.uid', ondelete="CASCADE"))
    device_name = db.Column(db.String(200), nullable=False)
    IMEI = db.Column(db.String(100), nullable=False)
    UDID = db.Column(db.String(200), nullable=False)
    model = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return "<Device '%r': %r>" % (self.device_name, self.owner)
