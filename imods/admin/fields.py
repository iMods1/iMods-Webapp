from imods import app
from imods.models import User
from imods.helpers import generate_bucket_key
from imods.tasks.dpkg import upload_to_s3, delete_from_s3
from werkzeug import FileStorage
from flask.ext.admin.form.upload import ImageUploadField, ImageUploadInput
from tempfile import mkstemp


class S3ImageUploadInput(ImageUploadInput):
    def get_url(self, field):
        if not isinstance(field, S3ImageUploadField):
            raise TypeError("field argument must be an instance of S3ImageUploadField")

        if field.data and not isinstance(field.data, FileStorage):
            s3_key = app.s3_assets_bucket.get_key(field.data)
            if not s3_key:
                return ''
            else:
                return s3_key.generate_url(app.config["DOWNLOAD_URL_EXPIRES_IN"])
        else:
            return ''


class S3ImageUploadField(ImageUploadField):
    """ See flask.ext.admin.fields.ImageUploadField for more details. """
    widget = S3ImageUploadInput()

    def __init__(self, s3_bucket, s3_keypath_gen, *args, **kwargs):
        super(S3ImageUploadField, self).__init__(*args, **kwargs)
        self._s3_bucket = s3_bucket
        self._s3_keypath_gen = s3_keypath_gen or gen_profile_img_s3_keypath
        if s3_bucket is None:
            raise ValueError("s3_bucket cannot be None.")
        if self._s3_keypath_gen is None:
            raise ValueError("s3_keypath_gen cannot be None.")
        self._s3_keypath = None

    def populate_obj(self, obj, name):
        # Generate S3 keypath
        if not self._s3_keypath:
            self._s3_keypath = self._s3_keypath_gen(self, obj)

        field = getattr(obj, name, None)
        if field:
            if self._should_delete:
                self._delete_file(field)
                setattr(obj, name, None)
                return

        if self.data and isinstance(self.data, FileStorage):
            _, tmpfilename = mkstemp()
            self._save_file(self.data, tmpfilename)
            upload_to_s3.delay(self._s3_bucket,
                               self._s3_keypath,
                               tmpfilename,
                               True)
            setattr(obj, name, self._s3_keypath)

    def _get_path(self, filename):
        return filename

    def _delete_file(self, s3_keypath):
        delete_from_s3.delay(self._s3_bucket, s3_keypath)

    def _save_thumbnail(self, data, filename, format):
        pass

    def _get_save_format(self, filename, image):
        return filename, image.format


def gen_profile_img_s3_keypath(field, obj):
    if not isinstance(obj, User):
        raise TypeError("%r is not a User record.")
    keypath = generate_bucket_key(app.config["S3_MEDIA_BASE_PATH"],
                                  "profile_img_%s" % str(obj.uid),
                                  field.data.filename)
    return keypath
