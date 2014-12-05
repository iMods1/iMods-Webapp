from imods import db, app
from imods.models import User, BillingInfo, Category, Device, Item, Order
from imods.models import UserRole, BillingType, OrderStatus, Review, Banner
from imods.helpers import db_scoped_session, generate_bucket_key, detect_tweak
from imods.tasks.dpkg import dpkg_update_index, upload_to_s3
from flask.ext.admin import Admin, expose, helpers, AdminIndexView, BaseView
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.admin.helpers import get_form_data
from flask import session, redirect, url_for, request, flash
from werkzeug import check_password_hash, generate_password_hash
import wtforms as wtf
from flask.ext.wtf import Form as ExtForm
from apt import debfile
from apt_pkg import TagSection
from os import path
import os
from tempfile import mkstemp
import shutil
import hashlib
from .fields import S3ImageUploadField, S3DebFileUploadField
from .fields import S3YouTubeVideoLinkUploadField, S3PKGAssetsImageUploadField
from .fields import gen_app_icon_s3_keypath, gen_profile_img_s3_keypath
from .fields import gen_youtublinkfile_s3_key_path
from .fields import gen_screenshot_s3_keypath, gen_banner_s3_keypath
from .validators import validate_imgfile, validate_debfile


class UserView(ModelView):
    form_overrides = dict(role=wtf.SelectField,
                          password=wtf.PasswordField)
    form_args = dict(
        role=dict(
            choices=[(UserRole.Admin, "Admin"),
                     (UserRole.SiteAdmin, "SiteAdmin"),
                     (UserRole.User, "User")
                     ],
            coerce=int
        ),
        password=dict(
            validators=[wtf.validators.Length(min=3, max=100)]
        ),
        email=dict(
            validators=[wtf.validators.Email(message="Invalid email address")]
        )
    )

    def get_edit_form(self):
        form_class = super(UserView, self).scaffold_form()
        validators = [wtf.validators.Length(min=3, max=100),
                      wtf.validators.Optional()]
        form_class.new_password = wtf.PasswordField('New Password',
                                                    validators=validators)
        form_class.password = wtf.HiddenField()

        form_class.profile_image_s3_keypath = S3ImageUploadField(
            s3_bucket=app.config["S3_ASSETS_BUCKET"],
            s3_keypath_gen=gen_profile_img_s3_keypath,
            label=u'Profile image',
            base_path=app.config["S3_MEDIA_BASE_PATH"])
        return form_class

    def on_model_change(self, form, model, is_created):
        if is_created:
            model.password = generate_password_hash(form.password.data)
        else:
            plainpwd = form.new_password.data.strip()
            if plainpwd:
                newpwd = generate_password_hash(form.new_password.data)
                model.password = newpwd

    def is_accessible(self):
        return session.get('user') is not None

    def __init__(self, session, **kwargs):
        super(UserView, self).__init__(User, session, **kwargs)


class BillingView(ModelView):
    form_overrides = dict(type_=wtf.SelectField)
    form_args = dict(
        type_=dict(
            choices=[(BillingType.creditcard, "Credit Card"),
                     (BillingType.paypal, "Paypal"),
                     ],
            label="Payment type"
        ))

    def is_accessible(self):
        return session.get('user') is not None

    def __init__(self, session, **kwargs):
        super(BillingView, self).__init__(BillingInfo, session, **kwargs)


class OrderView(ModelView):
    form_overrides = dict(status=wtf.SelectField)
    form_args = dict(
        status=dict(
            choices=[(OrderStatus.OrderPlaced, "Placed"),
                     (OrderStatus.OrderCompleted, "Completed"),
                     (OrderStatus.OrderCancelled, "Cancelled")
                     ],
            coerce=int,
            label="Order status"
        ))

    def is_accessible(self):
        return session.get('user') is not None

    def __init__(self, session, **kwargs):
        super(OrderView, self).__init__(Order, session, **kwargs)


class CategoryView(ModelView):

    def is_accessible(self):
        return session.get('user') is not None

    def __init__(self, session, **kwargs):
        super(CategoryView, self).__init__(Category, session, **kwargs)


class ItemView(ModelView):

    def is_accessible(self):
        return session.get('user') is not None

    def __init__(self, session, **kwargs):
        super(ItemView, self).__init__(Item, session, **kwargs)

    def get_form(self):
        form_class = super(ItemView, self).scaffold_form()

        s3_bucket = app.config["S3_ASSETS_BUCKET"]

        form_class.deb_file = S3DebFileUploadField(
            label=u'Deb file',
            validators=[validate_debfile, wtf.validators.Required()])

        form_class.app_icon = S3PKGAssetsImageUploadField(
            s3_bucket=s3_bucket,
            s3_keypath_gen=gen_app_icon_s3_keypath,
            s3_assets_dir="icons",
            should_populate_obj=False,
            auto_upload=True,
            label=u'App Icon',
            validators=[validate_imgfile])
        form_class.screenshot = S3PKGAssetsImageUploadField(
            s3_bucket=s3_bucket,
            s3_keypath_gen=gen_screenshot_s3_keypath,
            s3_assets_dir="screenshots",
            should_populate_obj=False,
            auto_upload=True,
            label=u'Screenshot',
            validators=[validate_imgfile])
        form_class.banner_image = S3PKGAssetsImageUploadField(
            s3_bucket=s3_bucket,
            s3_keypath_gen=gen_banner_s3_keypath,
            s3_assets_dir="banners",
            should_populate_obj=False,
            auto_upload=True,
            label=u'Banner Image',
            validators=[validate_imgfile])

        form_class.video = S3YouTubeVideoLinkUploadField(
            s3_bucket=s3_bucket,
            s3_assets_dir="videos",
            s3_keypath_gen=gen_youtublinkfile_s3_key_path,
            label=u'YouTube Video ID')

        return form_class

    def edit_form(self, obj=None):
        # Fill fields with data from obj
        form = super(ItemView, self).edit_form(obj=obj)
        form.deb_file.data = path.basename(obj.pkg_path)
        form.app_icon.fill_with_obj(obj)
        form.screenshot.fill_with_obj(obj)
        form.banner_image.fill_with_obj(obj)
        form.video.fill_with_obj(obj)
        return form

    def on_model_change(self, form, model, is_created):
        # first, upload the deb
        form.deb_file.populate_obj(model, "", True)
        # Now pkg_assets_path is set
        try:
            form.app_icon.populate_obj(model, "", True)
            form.screenshot.populate_obj(model, "", True)
            form.banner_image.populate_obj(model, "", True)
            form.video.populate_obj(model, "", True)
        except TypeError as e:
            print e
            raise e


class DeviceView(ModelView):

    def is_accessible(self):
        return session.get('user') is not None

    def __init__(self, session, **kwargs):
        super(DeviceView, self).__init__(Device, session, **kwargs)


class ReviewView(ModelView):
    def is_accessible(self):
        return session.get('user') is not None

    def __init__(self, session, **kwargs):
        super(ReviewView, self).__init__(Review, session, **kwargs)


class BannerView(ModelView):
    def is_accessible(self):
        return session.get('user') is not None

    def __init__(self, session, **kwargs):
        super(BannerView, self).__init__(Banner, session, **kwargs)


class LoginForm(wtf.form.Form):
    email = wtf.fields.TextField(validators=[wtf.validators.required(),
                                             wtf.validators.Email()])
    password = wtf.fields.PasswordField(validators=[wtf.validators.required()])

    def validate_email(self, field):
        user = self.get_user()
        if user is None:
            raise wtf.validators.ValidationError("Invalid user")

        if not check_password_hash(user.password, self.password.data):
            raise wtf.validators.ValidationError("Invalid password")

        if user.role != UserRole.SiteAdmin:
            raise wtf.validators.ValidationError(
                "You don't have the required permission to access this page.")

        user_session_dict = {
            'fullname': user.fullname,
            'email': user.email,
            'role': user.role
        }
        session['user'] = user_session_dict

    def get_user(self):
        return User.query.filter_by(email=self.email.data).first()


class iModsAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if not session.get('user'):
            return redirect(url_for('.login_view'))
        elif session['user']['role'] != UserRole.SiteAdmin:
            del session['user']
        return redirect(url_for(".login_view"))

    @expose('/login', methods=["GET", "POST"])
    def login_view(self):
        form = LoginForm(request.form)
        user = None
        if helpers.validate_form_on_submit(form):
            user = form.get_user()

        if user and user.role == UserRole.SiteAdmin:
            return redirect(url_for('.index'))

        self._template_args['form'] = form
        return super(iModsAdminIndexView, self).index()

    @expose('/logout')
    def logout_view(self):
        if session.get('user'):
            del session['user']
        return redirect(url_for(".index"))


class PackageAssetsUploadForm(ExtForm):
    item_id = wtf.fields.SelectField(u"Item", coerce=int)
    app_icon = wtf.fields.FileField(u"App Icon")
    screenshot = wtf.fields.FileField(u"Screenshot")
    youtube_video_id = wtf.fields.TextField(u"Youtube Video Identifier")
    package_file = wtf.fields.FileField(u'Package file(deb)')
    banner_image = wtf.fields.FileField(u'Banner Image')

    def validate_imgfile(self, field):
        if field.data:
            filename = field.data.name.lower()

            ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])
            ext = filename.rsplit('.', 1)
            if not ('.' in filename and ext in ALLOWED_EXTENSIONS):
                raise wtf.validators.ValidationError(
                    'Wrong Filetype, you can upload only png,jpg,jpeg files')

    def validate_debfile(self, field):
        if field.data:
            filename = field.data.name.lower()
            _, ext = path.splitext(filename)
            if ext != ".deb":
                raise wtf.validators.ValidationError(
                    'You can only upload deb files')

    def validate_package_file(self, field):
        return self.validate_debfile(field)

    def validate_app_icon(self, field):
        return self.validate_imgfile(field)

    def validate_screenshot(self, field):
        return self.validate_imgfile(field)

    def validate_banner_image(self, field):
        return self.validate_imgfile(field)


class PackageAssetsView(BaseView):
    template_name = u"package_assets.html"

    def is_accessible(self):
        return session.get('user') is not None

    @expose('/', methods=["GET", "POST"])
    def index(self):

        form = PackageAssetsUploadForm(request.form)

        # Populate choices for select field
        with db_scoped_session() as s:
            items = s.query(Item).all()
            form.item_id.choices = [(item.iid, item.display_name)
                                    for item in items]

            if helpers.validate_form_on_submit(form):
                # from boto.s3.key import Key
                # Get file data from request.files
                app_icon = request.files["app_icon"]
                screenshot = request.files["screenshot"]
                # Get package file
                package_file = request.files["package_file"]
                # Get banner image file
                banner_img_file = request.files["banner_image"]
                # Get pkg_assets_path
                item = s.query(Item).get(form.item_id.data)

                _, debTmpFile = mkstemp()
                with open(debTmpFile, "wb") as local_deb_file:
                    local_deb_file.write(package_file.read())
                sha1 = hashlib.sha1()
                sha1.update(open(debTmpFile, 'rb').read())
                deb_sha1_digest = sha1.hexdigest()

                try:
                    # Verify and update item information based on package file
                    deb_obj = debfile.DebPackage(debTmpFile)
                    item.control = deb_obj.control_content("control")
                    tags = TagSection(item.control)
                    item.pkg_dependencies = tags.get("Depends", "")
                    item.pkg_version = tags.get("Version", "")
                    item.pkg_signature = deb_sha1_digest
                    item.description = tags.get("Description", "")

                    # Create local package path
                    pkg_fullname = item.pkg_name + '-' + str(item.pkg_version)
                    base_path = path.join(
                        "packages",
                        item.pkg_name,
                        pkg_fullname,
                        'assets')
                    item.pkg_assets_path = base_path

                    pkg_name = tags.get("Package", None)

                    if (pkg_name is not None) and pkg_name != item.pkg_name:
                        # Check if the name already exists
                        t_item = s.query(Item).filter_by(pkg_name=pkg_name).first()
                        if t_item is None or t_item.iid == item.iid:
                            item.pkg_name = pkg_name
                        else:
                            flash("Package name '%s' is used by another "
                                  "item(%d)." % (pkg_name, t_item.iid))
                            s.rollback()
                            os.unlink(debTmpFile)
                            return redirect(url_for(".index"))

                    # Build package path
                    pkg_path = path.join(
                        "packages",
                        item.pkg_name)

                    assets_bucket = app.config.get("S3_ASSETS_BUCKET")
                    pkg_bucket = app.config.get("S3_PKG_BUCKET")

                    pkg_s3_key_path = generate_bucket_key(
                        pkg_path,
                        pkg_fullname,
                        package_file.filename)
                    item.pkg_path = pkg_s3_key_path

                    pkg_local_cache_path = path.join(
                        app.config["DEB_UPLOAD_PATH"],
                        pkg_s3_key_path)

                    # Local package path
                    pkg_local_cache_dir = path.dirname(pkg_local_cache_path)
                    if not path.exists(pkg_local_cache_dir):
                        print("Creating path %s" % pkg_local_cache_dir)
                        os.makedirs(pkg_local_cache_dir)

                    # Move tmp deb file to the cache folder
                    shutil.move(debTmpFile, pkg_local_cache_path)

                    pkg_overrides = [(item.pkg_name, "itemid", item.iid),
                                     (item.pkg_name, "itemname", item.display_name),
                                     (item.pkg_name, "filename", "null")]

                    # Check if it's a tweak
                    tweak_file = detect_tweak(deb_obj.filelist)
                    if tweak_file is not None:
                        tweak_file = 'file:///' + tweak_file
                        pkg_overrides.append((item.pkg_name, "Respring", "YES",))
                        pkg_overrides.append((item.pkg_name, "TweakLib", tweak_file,))


                    index_s3_key_path = "Packages.gz"

                    # Upload deb file
                    upload_to_s3.delay(pkg_bucket,
                                       pkg_s3_key_path,
                                       pkg_local_cache_path)
                    pkg_index_file = path.join(app.config["DEB_UPLOAD_PATH"],
                                               app.config["PKG_INDEX_FILE_NAME"]
                                               )
                    # Update and upload package index
                    dpkg_update_index.delay(app.config["DEB_UPLOAD_PATH"],
                                            pkg_bucket,
                                            index_s3_key_path,
                                            pkg_index_file,
                                            pkg_overrides)

                    # Upload icon
                    icon_base_path = path.join(base_path, "icons")
                    icon_s3_path = generate_bucket_key(icon_base_path,
                                                       "app_icon",
                                                       app_icon.filename)
                    _, icon_tmpfile = mkstemp()
                    with open(icon_tmpfile, "wb") as tmp:
                        tmp.write(app_icon.read())
                    upload_to_s3.delay(assets_bucket, icon_s3_path, icon_tmpfile, True)

                    # Upload screenshot
                    ss_base_path = path.join(base_path, "screenshots")
                    sshot_s3_path = generate_bucket_key(ss_base_path,
                                                        "screenshot",
                                                        screenshot.filename)
                    _, sshot_tmpfile = mkstemp()
                    with open(sshot_tmpfile, "wb") as tmp:
                        tmp.write(screenshot.read())
                    upload_to_s3.delay(assets_bucket, sshot_s3_path, sshot_tmpfile, True)

                    # Upload youtube video id
                    youtube_id_path = path.join(base_path, "videos")
                    youtube_s3_filename = "youtube-%s" % form.youtube_video_id.data
                    youtube_id_s3_path = path.join(youtube_id_path,
                                                   youtube_s3_filename)
                    _, youtube_id_tmpfile = mkstemp()
                    with open(youtube_id_tmpfile, "wb") as tmp:
                        tmp.write(form.youtube_video_id.data)
                    upload_to_s3.delay(assets_bucket, youtube_id_s3_path, youtube_id_tmpfile, True)


                    # Upload banner image
                    banner_img_path = path.join(base_path, "banners")
                    banner_img_s3_path = generate_bucket_key(banner_img_path,
                                                             "banner_image",
                                                             banner_img_file.filename)

                    _, banner_img_tmpfile = mkstemp()
                    with open(banner_img_tmpfile, "wb") as tmp:
                        tmp.write(banner_img_file.read())
                    # Add banner item to the database
                    with db_scoped_session() as ses:
                        banner = ses.query(Banner).filter_by(item_id = item.iid).first()
                        if banner is None:
                            banner = Banner(item_id=item.iid)
                            ses.add(banner)
                            ses.commit()
                    upload_to_s3.delay(assets_bucket, banner_img_s3_path, banner_img_tmpfile, True)

                except Exception as e:
                    s.rollback()
                    raise e

                # Commit changes
                s.commit()

                flash("Assets uploaded successfully")
                return redirect(url_for('.index'))

        context = {'form': form}
        return self.render(self.template_name, **context)


imods_admin = Admin(name="iMods Admin",
                    index_view=iModsAdminIndexView(),
                    base_template="admin_master.html")
imods_admin.add_view(UserView(db.session))
imods_admin.add_view(DeviceView(db.session))
imods_admin.add_view(BillingView(db.session))
imods_admin.add_view(CategoryView(db.session))
imods_admin.add_view(ItemView(db.session))
imods_admin.add_view(BannerView(db.session))
imods_admin.add_view(OrderView(db.session))
imods_admin.add_view(ReviewView(db.session))
# imods_admin.add_view(PackageAssetsView(name="Manage Assets"))
