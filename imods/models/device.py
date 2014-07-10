from imods import db
from imods.models.mixin import JsonSerialize


class Device(db.Model, JsonSerialize):
    __tablename__ = "DEVICE"
    __public__ = ("owner", "device_name", "IMEI", "UDID", "model")

    uid = db.Column(db.Integer, db.ForeignKey('USER.uid', ondelete="CASCADE"))
    device_name = db.Column(db.String(200), nullable=False)
    IMEI = db.Column(db.String(100), nullable=False)
    UDID = db.Column(db.String(200), nullable=False, primary_key=True)
    model = db.Column(db.String(100), nullable=False)

    def __init__(self, device_name, IMEI, UDID, model):
        self.device_name = device_name
        self.IMEI = IMEI
        self.UDID = UDID
        self.model = model

    def __repr__(self):
        return "<Device '%r': %r>" % (self.device_name, self.owner)
