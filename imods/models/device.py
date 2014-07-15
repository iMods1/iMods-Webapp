from imods import db
from imods.models.mixin import JsonSerialize


class Device(db.Model, JsonSerialize):
    __tablename__ = "DEVICE"
    __public__ = ("uid", "device_name", "IMEI", "UDID", "model")

    dev_id = db.Column(db.Integer, nullable=False, primary_key=True)
    uid = db.Column(db.Integer, db.ForeignKey('USER.uid', ondelete="CASCADE"))
    device_name = db.Column(db.String(200), nullable=False)
    IMEI = db.Column(db.String(100), nullable=False)
    UDID = db.Column(db.String(200), nullable=False)
    model = db.Column(db.String(100), nullable=False)

    def __init__(self, user_id, device_name, IMEI, UDID, model):
        self.uid = user_id
        self.device_name = device_name
        self.IMEI = IMEI
        self.UDID = UDID
        self.model = model

    def __repr__(self):
        return "<Device '%r': %r>" % (self.device_name, self.owner)
