from imods import app
from imods.models import User, Item
from imods.helpers import generate_bucket_key, detect_tweak, db_scoped_session
from imods.tasks.dpkg import upload_to_s3, delete_from_s3, dpkg_update_index
from werkzeug import FileStorage
from flask.ext.admin.form.upload import ImageUploadField, ImageUploadInput, FileUploadField

# Youtube API Libraries
from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.tools import argparser

import hashlib
import wtforms as wtf
from tempfile import mkstemp
from apt import debfile
from apt_pkg import TagSection
from os import path
import os
import shutil
from wtforms.widgets import HTMLString, html_params
try:
    from wtforms.fields.core import _unset_value as unset_value
except ImportError:
    from wtforms.utils import unset_value


class S3ImageUploadInput(ImageUploadInput):
    def get_url(self, field):
        if not isinstance(field, S3ImageUploadField):
            raise TypeError("field argument must be an instance of S3ImageUploadField")

        if hasattr(field, 'data') and not isinstance(field.data, FileStorage):
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

    def __init__(self, s3_bucket, s3_keypath_gen, s3_base_path=None,
                 should_populate_obj=True, auto_upload=True, *args, **kwargs):
        super(S3ImageUploadField, self).__init__(*args, **kwargs)
        self._s3_bucket = s3_bucket
        self._s3_keypath_gen = s3_keypath_gen
        if s3_bucket is None:
            raise TypeError("s3_bucket cannot be None.")
        if self._s3_keypath_gen is None:
            raise TypeError("s3_keypath_gen cannot be None.")
        self._s3_keypath = None
        self._s3_basepath = s3_base_path or app.config["S3_MEDIA_BASE_PATH"]
        self._auto_upload = auto_upload
        self._should_populate_obj = should_populate_obj

    def upload_to_s3(self, filename):
        upload_to_s3.delay(self._s3_bucket, self._s3_keypath, filename, True)

    def gen_s3_keypath(self, obj, basepath=None):
        basepath = basepath or self._s3_basepath
        self._s3_keypath = self._s3_keypath_gen(basepath, self, obj)
        return self._s3_keypath

    def populate_obj(self, obj, name):
        field = getattr(obj, name, None)
        if field:
            if self._should_delete:
                self._delete_file(field)
                setattr(obj, name, None)
                return

        if self.data and isinstance(self.data, FileStorage):
            # Generate S3 keypath
            if not self._s3_keypath:
                self._s3_keypath = self.gen_s3_keypath(obj, self._s3_basepath)

            _, tmpfilename = mkstemp()
            self._save_file(self.data, tmpfilename)
            if self._auto_upload:
                self.upload_to_s3(tmpfilename)
            if self._should_populate_obj:
                setattr(obj, name, self._s3_keypath)

    def _get_path(self, filename):
        return filename

    def _delete_file(self, s3_keypath):
        delete_from_s3.delay(self._s3_bucket, s3_keypath)

    def _save_thumbnail(self, data, filename, format):
        pass

    def _get_save_format(self, filename, image):
        return filename, image.format


class S3PKGImageUploadInput(ImageUploadInput):
    def get_url(self, field):
        if not isinstance(field, S3ImageUploadField):
            raise TypeError("field argument must be an instance of S3ImageUploadField")

        if field._s3_keypath and not isinstance(field.data, FileStorage):
            s3_key = app.s3_assets_bucket.get_key(field._s3_keypath)
            if not s3_key:
                return ''
            else:
                return s3_key.generate_url(app.config["DOWNLOAD_URL_EXPIRES_IN"])
        else:
            return ''


class S3PKGAssetsImageUploadField(S3ImageUploadField):
    widget = S3PKGImageUploadInput()

    def __init__(self, s3_assets_dir=None, *args, **kwargs):
        self._s3_assets_dir = s3_assets_dir
        super(S3PKGAssetsImageUploadField, self).__init__(*args, **kwargs)

    def populate_obj(self, obj, name, override=False):
        if not override:
            return
        if not isinstance(obj, Item):
            raise TypeError("obj must be of type Item")
        self._s3_basepath = obj.pkg_assets_path

        if self._should_delete:
            self._delete_file(self._s3_keypath)
        super(S3PKGAssetsImageUploadField, self).populate_obj(obj, name)

    def fill_with_obj(self, obj, filename=None):
        if not isinstance(obj, Item) or not obj.pkg_assets_path:
            return
        self._s3_basepath = obj.pkg_assets_path
        s3_list = app.s3_assets_bucket.list(path.join(self._s3_basepath,
                                                      self._s3_assets_dir))
        files = filter(lambda x: not x.name.endswith('/'), s3_list)
        if files:
            if filename is None:
                self._s3_keypath = files[0].name
                self.data = self._s3_keypath
            elif filename is not None:
                for image in files:
                    if filename in image.name:
                        self._s3_keypath = image.name
                        self.data = self._s3_keypath
                        return
                self._s3_keypath = None
                self.data = self._s3_keypath


class S3DebFileUploadInput(object):
    empty_template = ("<input %(file)s>")
    data_template = ("<div>"
                     " <input %(text)s>"
                     " <input %(file)s>"
                     "</div>")

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        kwargs.setdefault('name', field.name)
        
        val = ''
        template = self.data_template
        try:
            val = field.data
        except AttributeError:
            val = ''
            template = self.empty_template
        return HTMLString(template % {
            'text': html_params(type="text",
                                readonly="readonly",
                                value=val),
            'file': html_params(type="file",
                                **kwargs)
        })


class S3DebFileUploadField(FileUploadField):
    widget = S3DebFileUploadInput()

    def __init__(self, s3_bucket=None, *args, **kwargs):
        super(S3DebFileUploadField, self).__init__(allowed_extensions=["deb"],
                                                   *args, **kwargs)
        self._s3_bucket = s3_bucket or app.config["S3_PKG_BUCKET"]
        self._deb_tmpfile = None
        self._deb_file_input = None

    def pre_validate(self, form):
        if not self._deb_file_input or not isinstance(self._deb_file_input, FileStorage):
            return

        # Save the deb file to a tmp file
        _, debtmp = mkstemp()
        with open(debtmp, "wb") as tmp:
            tmp.write(self._deb_file_input.read())
        # Open the deb file and parse control information
        deb_obj = debfile.DebPackage(debtmp)
        tags = TagSection(deb_obj.control_content("control"))
        pkg_name = tags.get('Package', None)

        if pkg_name is None:
            # Remove the tmpfile
            os.unlink(debtmp)
            raise wtf.ValidationError("Invalid deb control file, "
                                      "package name is empty.")

        # Check 'unique' property on pkg_name
        with db_scoped_session() as se:
            obj_t = se.query(Item).filter_by(pkg_name=pkg_name).first()
            if obj_t != None and hasattr(form, 'iid') and obj_t.iid != form.iid.data:
                # obj exists, raise error
                raise wtf.ValidationError("The same package name found in "
                                          "%s" % obj_t)

        # Validation successful, fill the tmpfile path
        self._deb_tmpfile = debtmp
        self.data = debtmp

    def process(self, formdata, data=unset_value):
        if formdata and formdata.has_key('deb_file'):
            self._deb_file_input = formdata['deb_file']

    def populate_obj(self, obj, name, override=False):
        if not isinstance(obj, Item):
            raise TypeError("obj argument must be of type Item")

        if not override:
            return

        if not self._deb_file_input or not isinstance(self._deb_file_input, FileStorage):
            return

        # clean old deb file first
        if obj.pkg_path:
            old_local_cache_path = path.join(app.config["DEB_UPLOAD_PATH"],
                                             obj.pkg_path)
            if path.exists(old_local_cache_path):
                os.unlink(old_local_cache_path)

        sha1 = hashlib.sha1()
        sha1.update(open(self._deb_tmpfile, 'rb').read())
        deb_sha1_digest = sha1.hexdigest()

        # Get package information from the deb file and populate the Item object
        deb_obj = debfile.DebPackage(self._deb_tmpfile)
        obj.control = deb_obj.control_content("control")
        tags = TagSection(obj.control)
        obj.pkg_dependencies = tags.get("Depends", "")
        obj.pkg_predepends = tags.get("Pre-Depends", "")
        obj.pkg_conflicts = tags.get("Conflicts", "")
        obj.pkg_version = tags.get("Version", "")
        obj.pkg_signature = deb_sha1_digest
        obj.description = tags.get("Description", "")
        pkg_name = tags.get("Package", None)
        obj.pkg_name = pkg_name

        pkg_fullname = obj.pkg_name + '-' + str(obj.pkg_version)
        base_path = path.join(
            "packages",
            obj.pkg_name,
            pkg_fullname,
            'assets')
        obj.pkg_assets_path = base_path
        pkg_path, pkg_s3_key_path = self._gen_pkg_paths(obj,
                                                        pkg_fullname,
                                                        self._deb_file_input.filename)
        obj.pkg_path = pkg_s3_key_path

        pkg_local_cache_path = path.join(
            app.config["DEB_UPLOAD_PATH"],
            pkg_s3_key_path)

        # Local package path
        pkg_local_cache_dir = path.dirname(pkg_local_cache_path)
        if not path.exists(pkg_local_cache_dir):
            os.makedirs(pkg_local_cache_dir)

        # Move tmp deb file to the cache folder
        shutil.move(self._deb_tmpfile, pkg_local_cache_path)
        self._deb_tmpfile = pkg_local_cache_path

    def after_populate_obj(self, obj):
        if not self._deb_file_input or not isinstance(self._deb_file_input, FileStorage):
            return
        # Rebuild index and upload the deb file, can only be called in after_model_change()
        # We need to postpone upload because the item id (primary key) won't be set until the transaction is done

        # Sanity checks
        if not obj or not obj.iid:
            raise Exception("Deb uploading failed: item or item id is none.")

        # We need some extra information of the package added to the index file
        # dpkg_scan takes an additional file 'overrides' when generating the index file
        changelog = obj.changelog
        if changelog is None:
            changelog = " "
        summary = obj.summary
        if summary is None:
            summary = " "
            #                         (obj.pkg_name, "filename", "null"),
        pkg_overrides = [(obj.pkg_name, "itemid", obj.iid),
                         (obj.pkg_name, "itemname", obj.display_name),
                         (obj.pkg_name, "authorid", obj.author_id),
                         (obj.pkg_name, "price", str(obj.price)),
                         (obj.pkg_name, "pkgversion", obj.pkg_version),
                         (obj.pkg_name, "pkgchangelog", changelog),
                         (obj.pkg_name, "pkgsummary", summary)]

        deb_obj = debfile.DebPackage(self._deb_tmpfile)
        # Check if it's a tweak
        tweak_file = detect_tweak(deb_obj.filelist)
        if tweak_file is not None:
            tweak_file = 'file:///' + tweak_file
            pkg_overrides.append((obj.pkg_name, "Respring", "YES",))
            pkg_overrides.append((obj.pkg_name, "TweakLib", tweak_file,))

        index_s3_key_path = "Packages.gz"
        pkg_index_file = path.join(app.config["DEB_UPLOAD_PATH"],
                                   app.config["PKG_INDEX_FILE_NAME"])
        dpkg_update_index.delay(app.config["DEB_UPLOAD_PATH"],
                                self._s3_bucket,
                                index_s3_key_path,
                                pkg_index_file,
                                pkg_overrides)
        # Upload deb file to S3
        self._upload_to_s3(obj.pkg_path)


    def _gen_pkg_paths(self, obj, pkg_fullname, filename):
        # Build package path
        pkg_path = path.join(
            "packages",
            obj.pkg_name)
        pkg_s3_key_path = generate_bucket_key(pkg_path, pkg_fullname, filename)
        return pkg_path, pkg_s3_key_path

    def _upload_to_s3(self, s3_keypath):
        if not self._deb_tmpfile:
            raise Exception("The deb file was not save to the tmp file, "
                            "cannot upload.")
        upload_to_s3.delay(self._s3_bucket,
                           s3_keypath,
                           self._deb_tmpfile,
                           False)

    def _delete_file(self, obj):
        if getattr(obj, "pkg_path", None):
            return
        delete_from_s3.delay(self._s3_bucket, obj.pkg_path)
    def _save_file(self, data, filename):
        pass


class S3YouTubeVideoLinkUploadInput(object):
    data_template = (
                     '<input %(video)s>'
                     '<input type="checkbox" name="%(marker)s">Delete</input>'
                     '<div>'
                     '<iframe id="ytplayer" type="text/html" width="640" height="390"'
                     ' src="http://www.youtube.com/embed/%(vid)s?autoplay=0"'
                     ' frameborder="0">'
                     '</iframe>'
                     '</div>'
                     )
    empty_template = ('<input %(video)s>')

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        kwargs.setdefault('name', field.name)

        template = self.data_template if field._s3_keypath else self.empty_template

        return HTMLString(template % {
            'vid': field.data,
            'marker': '_%s-delete' % field.name,
            'video': html_params(type="text",
                                 value=field.data or '',
                                 **kwargs)
        })


class S3YouTubeVideoLinkUploadField(wtf.TextField):
    widget = S3YouTubeVideoLinkUploadInput()

    def __init__(self, s3_bucket, s3_base_path=None, s3_assets_dir=None,
                 s3_keypath_gen=None, *args, **kwargs):
        self._s3_bucket = s3_bucket or app.config["S3_ASSETS_BUCKET"]
        self._s3_basepath = s3_base_path
        self._s3_keypath_gen = s3_keypath_gen or gen_youtublinkfile_s3_key_path
        self._s3_keypath = None
        self._s3_assets_dir = s3_assets_dir
        self._should_delete = False
        super(S3YouTubeVideoLinkUploadField, self).__init__(*args, **kwargs)

    def process(self, formdata, data=unset_value):
        if formdata:
            marker = '_%s-delete' % self.name
            if marker in formdata:
                self._should_delete = True

        return super(S3YouTubeVideoLinkUploadField, self).process(formdata, data)

    def pre_validate(self, form):
        if not self.data or not isinstance(self.data, (unicode, str)):
            return
        youtube = build(app.config.get("YOUTUBE_API_SERVICE_NAME"),
            app.config.get("YOUTUBE_API_VERSION"),
            developerKey=app.config.get("DEVELOPER_KEY"))
            
        # Call the videos.list method to retrieve results matching the specified
        # video id.
        options = {"id" : self.data}
        video_response = youtube.videos().list(
            id=self.data,
            part="id"
        ).execute()
        valid = False
        if video_response != None and video_response['pageInfo'] != None\
            and video_response['pageInfo']['totalResults'] != None\
            and video_response['pageInfo']['totalResults'] > 0:
                valid = True
        if not valid:
            raise wtf.ValidationError("Video %s doesn't exist"	
                                      ", or it's not publicly available"		
                                      % self.data)

    def populate_obj(self, obj, name, override=False):
        if not isinstance(obj, Item):
            raise TypeError("obj must be of type Item")

        if not override or not self.data:
            return

        # Just delete video
        if self._should_delete:
            self._delete_video()
            return

        # Don't upload the same video twice
        if self.data and self._s3_keypath and self.data == path.basename(self._s3_keypath):
            return

        if self._s3_keypath:
            self._delete_video()
        self._s3_keypath = self._s3_keypath_gen(self._s3_basepath, self, obj)

        _, tmpfile = mkstemp()
        with open(tmpfile, "wb") as t:
            t.write(self.data)
        upload_to_s3.delay(self._s3_bucket, self._s3_keypath, tmpfile, True)

    def gen_s3_keypath(self, obj, basepath=None):
        self._s3_keypath = self._s3_keypath_gen(basepath, self, obj)
        return self._s3_keypath

    def fill_with_obj(self, obj):
        if not isinstance(obj, Item) or not obj.pkg_assets_path:
            return
        self._s3_basepath = obj.pkg_assets_path
        s3_list = app.s3_assets_bucket.list(path.join(self._s3_basepath,
                                                      self._s3_assets_dir))
        files = filter(lambda x: not x.name.endswith('/'), s3_list)
        if files:
            self._s3_keypath = files[0].name
            self.data = path.basename(self._s3_keypath).split('-', 1)[1]

    def _delete_video(self):
        if not self._s3_keypath:
            return
        delete_from_s3.delay(self._s3_bucket, self._s3_keypath)


def gen_profile_img_s3_keypath(basepath, field, obj):
    if not isinstance(obj, User):
        raise TypeError("%r is not a User object.")
    keypath = generate_bucket_key(basepath,
                                  "profile_img_%s" % str(obj.uid),
                                  field.data.filename)
    return keypath


def gen_app_icon_s3_keypath(basepath, field, obj):
    if not isinstance(obj, Item):
        raise TypeError("%r is not an Item object.")
    if not hasattr(field, 'data'):
        return
    basepath = obj.pkg_assets_path
    keypath = generate_bucket_key(path.join(basepath, field._s3_assets_dir),
                                  "app_icon",
                                  field.data.filename)
    return keypath


def gen_screenshot1_s3_keypath(basepath, field, obj):
    if not isinstance(obj, Item):
        raise TypeError("%r is not an Item object.")
    if not hasattr(field, 'data'):
        return
    basepath = obj.pkg_assets_path
    keypath = generate_bucket_key(path.join(basepath, field._s3_assets_dir),
                                  "screenshot1",
                                  field.data.filename)
    return keypath


def gen_screenshot2_s3_keypath(basepath, field, obj):
    if not isinstance(obj, Item):
        raise TypeError("%r is not an Item object.")
    if not hasattr(field, 'data'):
        return
    basepath = obj.pkg_assets_path
    keypath = generate_bucket_key(path.join(basepath, field._s3_assets_dir),
                                  "screenshot2",
                                  field.data.filename)
    return keypath


def gen_screenshot3_s3_keypath(basepath, field, obj):
    if not isinstance(obj, Item):
        raise TypeError("%r is not an Item object.")
    if not hasattr(field, 'data'):
        return
    basepath = obj.pkg_assets_path
    keypath = generate_bucket_key(path.join(basepath, field._s3_assets_dir),
                                  "screenshot3",
                                  field.data.filename)
    return keypath


def gen_screenshot4_s3_keypath(basepath, field, obj):
    if not isinstance(obj, Item):
        raise TypeError("%r is not an Item object.")
    if not hasattr(field, 'data'):
        return
    basepath = obj.pkg_assets_path
    keypath = generate_bucket_key(path.join(basepath, field._s3_assets_dir),
                                  "screenshot4",
                                  field.data.filename)
    return keypath


def gen_banner_s3_keypath(basepath, field, obj):
    if not isinstance(obj, Item):
        raise TypeError("%r is not an Item object.")
    if not hasattr(field, 'data'):
        return
    basepath = obj.pkg_assets_path
    keypath = generate_bucket_key(path.join(basepath, field._s3_assets_dir),
                                  "banner",
                                  field.data.filename)
    return keypath


def gen_youtublinkfile_s3_key_path(basepath, field, obj):
    if not isinstance(obj, Item):
        raise TypeError("%r is not an Item object.")
    if not hasattr(field, 'data'):
        return
    basepath = obj.pkg_assets_path
    link_filename = "youtube-%s" % field.data
    keypath = path.join(basepath, field._s3_assets_dir, link_filename)
    return keypath
