from imods import db, app
from imods.models import User, BillingInfo, Category, Device, Item, Order, VIPUsers
from imods.models import UserRole, BillingType, OrderStatus, Review, Banner, ItemStatus
from imods.helpers import db_scoped_session, generate_bucket_key, detect_tweak
from imods.tasks.dpkg import update_index, upload_to_s3, dpkg_update_index
from flask.ext.admin import Admin, expose, helpers, AdminIndexView, BaseView
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.admin.contrib.sqla.view import func
from flask.ext.admin.helpers import get_form_data
from flask import session, redirect, url_for, request, flash
from werkzeug import check_password_hash, generate_password_hash
import wtforms as wtf
from wtforms.fields import StringField
from wtforms.widgets import TextArea
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
from .fields import gen_screenshot1_s3_keypath, gen_screenshot2_s3_keypath,\
    gen_screenshot3_s3_keypath, gen_screenshot4_s3_keypath, gen_banner_s3_keypath
from .validators import validate_imgfile, validate_debfile

status_map = {
    0: "Approved",
    1: "Pending",
    2: "Rejected"
}

type_map = {
    "tweak": "Tweak",
    "theme": "Theme"
}

class UserView(ModelView):
    column_exclude_list = ('stripe_customer_token', 'password')
    form_overrides = dict(role=wtf.SelectField,
                          password=wtf.PasswordField,
                          stripe_customer_token=wtf.HiddenField)
    form_args = dict(
        role=dict(
            choices=[(UserRole.Admin, "Admin"),
                     (UserRole.SiteAdmin, "SiteAdmin"),
                     (UserRole.AppDev, "AppDev"),
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
    
    def is_visible(self):
        return (session.get('user')['role'] == UserRole.Admin or session.get('user')['role'] == UserRole.SiteAdmin)

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
    form_overrides = dict(type_=wtf.SelectField,
                          paypal_refresh_token=wtf.HiddenField,
                          stripe_card_token=wtf.HiddenField)
    form_args = dict(
        type_=dict(
            choices=[(BillingType.creditcard, "Credit Card"),
                     (BillingType.paypal, "Paypal"),
                     ],
            label="Payment type"
        ))

    column_exclude_list = ('stripe_card_token', 'paypal_refresh_token',
                           'cc_no', 'cc_name', 'cc_expr')
    
    def is_visible(self):
        return (session.get('user')['role'] == UserRole.Admin or session.get('user')['role'] == UserRole.SiteAdmin)

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
    
    def is_visible(self):
        return (session.get('user')['role'] == UserRole.Admin or session.get('user')['role'] == UserRole.SiteAdmin)

    def is_accessible(self):
        return session.get('user') is not None

    def __init__(self, session, **kwargs):
        super(OrderView, self).__init__(Order, session, **kwargs)


class CategoryView(ModelView):
    
    def is_visible(self):
        return (session.get('user')['role'] == UserRole.Admin or session.get('user')['role'] == UserRole.SiteAdmin)

    def is_accessible(self):
        return session.get('user') is not None

    def __init__(self, session, **kwargs):
        super(CategoryView, self).__init__(Category, session, **kwargs)


class ItemView(ModelView):

    def truncate_formatter(max_len, n):
        def fmt(v, c, m, p):
            t = getattr(m, n)
            if t:
                res = t[:max_len] + (t[max_len:] and '..')
            else:
                res = ''
            return res
        return fmt


    column_exclude_list = ('control', 'pkg_path', 'pkg_assets_path',
                           'pkg_signature', 'pkg_dependencies', 'changelog', 'pkg_conflicts', 'pkg_predepends')

    column_formatters = dict(description=truncate_formatter(15, 'description'),
                             summary=truncate_formatter(15, 'summary'),
                             status=lambda v, c, m, p: status_map[m.status])
    
    form_choices = {
        'status': [
            ('0', 'Approved'),
            ('1', 'Pending'),
            ('2', 'Rejected')
        ],
        'type': [
            ('tweak', 'Tweak'),
            ('theme', 'Theme')
        ]
    }
    
    
    def is_accessible(self):
        return session.get('user') is not None
    
    def get_query(self):
        role = session.get('user')['role']
        if role == UserRole.AppDev:
            return super(ItemView, self).get_query().filter(Item.author_id == session.get('user')['author_identifier'])
        return super(ItemView, self).get_query()
        
    def get_count_query(self):
      role = session.get('user')['role']
      if role == UserRole.AppDev:
          return self.session.query(func.count('*')).filter(self.model.author_id == session.get('user')['author_identifier'])
      return super(ItemView, self).get_count_query()

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
        form_class.screenshot1 = S3PKGAssetsImageUploadField(
            s3_bucket=s3_bucket,
            s3_keypath_gen=gen_screenshot1_s3_keypath,
            s3_assets_dir="screenshots",
            should_populate_obj=False,
            auto_upload=True,
            label=u'Screenshot 1',
            validators=[validate_imgfile])
        form_class.screenshot2 = S3PKGAssetsImageUploadField(
            s3_bucket=s3_bucket,
            s3_keypath_gen=gen_screenshot2_s3_keypath,
            s3_assets_dir="screenshots",
            should_populate_obj=False,
            auto_upload=True,
            label=u'Screenshot 2',
            validators=[validate_imgfile])
        form_class.screenshot3 = S3PKGAssetsImageUploadField(
            s3_bucket=s3_bucket,
            s3_keypath_gen=gen_screenshot3_s3_keypath,
            s3_assets_dir="screenshots",
            should_populate_obj=False,
            auto_upload=True,
            label=u'Screenshot 3',
            validators=[validate_imgfile])
        form_class.screenshot4 = S3PKGAssetsImageUploadField(
            s3_bucket=s3_bucket,
            s3_keypath_gen=gen_screenshot4_s3_keypath,
            s3_assets_dir="screenshots",
            should_populate_obj=False,
            auto_upload=True,
            label=u'Screenshot 4',
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
            
        form_class.changelog = StringField(u'Changelog', widget=TextArea())

        return form_class

    def edit_form(self, obj=None):
        # Fill fields with data from obj
        form = super(ItemView, self).edit_form(obj=obj)
        
        role = session.get('user')['role']
        if role == UserRole.AppDev:
            del form.status
        
        form.deb_file.data = path.basename(obj.pkg_path)
        form.app_icon.fill_with_obj(obj)
        form.screenshot1.fill_with_obj(obj, 'screenshot1')
        form.screenshot2.fill_with_obj(obj, 'screenshot2')
        form.screenshot3.fill_with_obj(obj, 'screenshot3')
        form.screenshot4.fill_with_obj(obj, 'screenshot4')
        form.banner_image.fill_with_obj(obj)
        form.video.fill_with_obj(obj)
        return form

    def on_model_change(self, form, model, is_created):
        if is_created:
            model.status = ItemStatus.Approved
            role = session.get('user')['role']
            author_id = session.get('user')['author_identifier']
            model.author_id = author_id
            if role == UserRole.AppDev:
                model.status = ItemStatus.Pending
            
            # model['type'] = 'theme'
            # tweak_file = detect_tweak([form.deb_file.data])
            # if tweak_file is not None:
            #     model['type'] = 'tweak'
        # populate model with information from the deb file
        form.deb_file.populate_obj(model, "", True)
        # Now pkg_assets_path is set
        try:
            form.app_icon.populate_obj(model, "", True)
            form.screenshot1.populate_obj(model, "", True)
            form.screenshot2.populate_obj(model, "", True)
            form.screenshot3.populate_obj(model, "", True)
            form.screenshot4.populate_obj(model, "", True)
            form.banner_image.populate_obj(model, "", True)
            form.video.populate_obj(model, "", True)
        except TypeError as e:
            print e
            raise e
            
    def on_model_delete(self, model):
        # Update and upload package index
        changelog = model.changelog
        if changelog is None:
            changelog = " "
        summary = model.summary
        if summary is None:
            summary = " "
            #(model.pkg_name, "filename", "null"),
        pkg_overrides = [(model.pkg_name, "itemid", model.iid),
                         (model.pkg_name, "itemname", model.display_name),
                         (model.pkg_name, "authorid", model.author_id),
                         (model.pkg_name, "price", str(model.price)),
                         (model.pkg_name, "pkgversion", model.pkg_version),
                         (model.pkg_name, "pkgchangelog", changelog),
                         (model.pkg_name, "pkgsummary", summary)]
        index_s3_key_path = "Packages.gz"
        pkg_index_file = path.join(app.config["DEB_UPLOAD_PATH"],
                                   app.config["PKG_INDEX_FILE_NAME"])
        dpkg_update_index.delay(app.config["DEB_UPLOAD_PATH"],
                                app.config["S3_ASSETS_BUCKET"],
                                index_s3_key_path,
                                pkg_index_file,
                                pkg_overrides)
            
    def after_model_change(self, form, model, is_created):
        # Upload deb file and index
        form.deb_file.after_populate_obj(model)
        changelog = model.changelog
        if changelog is None:
            changelog = " "
        summary = model.summary
        if summary is None:
            summary = " "
            #(model.pkg_name, "filename", "null"),
        pkg_overrides = [(model.pkg_name, "itemid", model.iid),
                         (model.pkg_name, "itemname", model.display_name),
                         (model.pkg_name, "authorid", model.author_id),
                         (model.pkg_name, "price", str(model.price)),
                         (model.pkg_name, "pkgversion", model.pkg_version),
                         (model.pkg_name, "pkgchangelog", changelog),
                         (model.pkg_name, "pkgsummary", summary)]
        index_s3_key_path = "Packages.gz"
        pkg_index_file = path.join(app.config["DEB_UPLOAD_PATH"],
                                   app.config["PKG_INDEX_FILE_NAME"])
        dpkg_update_index.delay(app.config["DEB_UPLOAD_PATH"],
                                app.config["S3_ASSETS_BUCKET"],
                                index_s3_key_path,
                                pkg_index_file,
                                pkg_overrides)



class DeviceView(ModelView):
    
    def is_visible(self):
        return (session.get('user')['role'] == UserRole.Admin or session.get('user')['role'] == UserRole.SiteAdmin)

    def is_accessible(self):
        return session.get('user') is not None

    def __init__(self, session, **kwargs):
        super(DeviceView, self).__init__(Device, session, **kwargs)


class ReviewView(ModelView):
    
    def is_visible(self):
        return (session.get('user')['role'] == UserRole.Admin or session.get('user')['role'] == UserRole.SiteAdmin)
        
    def is_accessible(self):
        return session.get('user') is not None

    def __init__(self, session, **kwargs):
        super(ReviewView, self).__init__(Review, session, **kwargs)


class VIPView(ModelView):
    
    def is_visible(self):
        return (session.get('user')['role'] == UserRole.Admin or session.get('user')['role'] == UserRole.SiteAdmin)
        
    def is_accessible(self):
        return session.get('user') is not None

    def __init__(self, session, **kwargs):
        super(VIPView, self).__init__(VIPUsers, session, **kwargs)

class BannerView(ModelView):
    
    def is_visible(self):
        return (session.get('user')['role'] == UserRole.Admin or session.get('user')['role'] == UserRole.SiteAdmin)
        
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

        if (user.role != UserRole.SiteAdmin and user.role != UserRole.AppDev):
            raise wtf.validators.ValidationError(
                "You don't have the required permission to access this page.")

        user_session_dict = {
            'fullname': user.fullname,
            'email': user.email,
            'role': user.role,
            'author_identifier': user.author_identifier
        }
        session['user'] = user_session_dict

    def get_user(self):
        return User.query.filter_by(email=self.email.data).first()

class RegisterForm(wtf.form.Form):
    email = wtf.fields.TextField(validators=[wtf.validators.required(), wtf.validators.Email()])
    password = wtf.fields.PasswordField(validators=[wtf.validators.required(), wtf.validators.EqualTo('confirm_password', message='Passwords must match')])
    confirm_password = wtf.fields.PasswordField(validators=[wtf.validators.required()])
    full_name = wtf.fields.TextField(validators=[wtf.validators.required()])
    age = wtf.fields.IntegerField()
    author_identifier = wtf.fields.TextField()
    status = wtf.fields.IntegerField(validators=[wtf.validators.required()])
    private_key = wtf.fields.TextField(validators=[wtf.validators.required()])
    summary = wtf.fields.TextField()
    secondary_email = wtf.fields.TextField()
    twitter = wtf.fields.TextField()

    def get_user(self):
        return User.query.filter_by(email=self.email.data).first()

class iModsAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if not session.get('user'):
            return redirect(url_for('.login_view'))
        elif session['user']['role'] != UserRole.SiteAdmin and session['user']['role'] != UserRole.AppDev:
            del session['user']
        return redirect(url_for(".login_view"))

    @expose('/login', methods=["GET", "POST"])
    def login_view(self):
        form = LoginForm(request.form)
        user = None
        if helpers.validate_form_on_submit(form):
            user = form.get_user()

        if user and (user.role == UserRole.SiteAdmin or user.role == UserRole.AppDev):
            return redirect(url_for('.index'))

        self._template_args['form'] = form
        return super(iModsAdminIndexView, self).index()

    @expose('/logout')
    def logout_view(self):
        if session.get('user'):
            del session['user']
        return redirect(url_for(".index"))

    @expose('/register', methods=["GET", "POST"])
    def register_view(self):
        form = RegisterForm(request.form)
        user = None
        if helpers.validate_form_on_submit(form):
            with db_scoped_session() as s:
                try:
                    new_user = User()
                    new_user.email = form.email.data
                    new_user.password = generate_password_hash(form.password.data)
                    new_user.fullname = form.full_name.data
                    new_user.age = form.age.data
                    new_user.author_identifier = form.author_identifier.data
                    new_user.status = form.status.data
                    new_user.private_key = form.private_key.data
                    new_user.secondary_email = form.secondary_email.data
                    new_user.summary = form.summary.data
                    new_user.twitter = form.twitter.data
                    
                    # Only AppDev users register from this page
                    new_user.role = UserRole.AppDev
                    s.add(new_user)
                    user_session_dict = {
                        'fullname': new_user.fullname,
                        'email': new_user.email,
                        'role': new_user.role,
                        'author_identifier': new_user.author_identifier
                    }
                    session['user'] = user_session_dict
                    user = form.get_user()
                except Exception as e:
                    s.rollback()
                    raise e

                # Commit changes
                s.commit()

        if user and (user.role == UserRole.SiteAdmin or user.role == UserRole.AppDev):
            return redirect(url_for('.index'))

        self._template_args['form'] = form
        return super(iModsAdminIndexView, self).index()

class PackageAssetsUploadForm(ExtForm):
    item_id = wtf.fields.SelectField(u"Item", coerce=int)
    app_icon = wtf.fields.FileField(u"App Icon")
    screenshot1 = wtf.fields.FileField(u"Screenshot 1")
    screenshot2 = wtf.fields.FileField(u"Screenshot 2")
    screenshot3 = wtf.fields.FileField(u"Screenshot 3")
    screenshot4 = wtf.fields.FileField(u"Screenshot 4")
    youtube_video_id = wtf.fields.TextField(u"Youtube Video Identifier")
    package_file = wtf.fields.FileField(u'Package file(deb)')
    banner_image = wtf.fields.FileField(u'Banner Image')

    def validate_imgfile(self, field):
        if hasattr(field, 'data'):
            filename = field.data.name.lower()

            ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])
            ext = filename.rsplit('.', 1)
            if not ('.' in filename and ext in ALLOWED_EXTENSIONS):
                raise wtf.validators.ValidationError(
                    'Wrong Filetype, you can upload only png,jpg,jpeg files')

    def validate_debfile(self, field):
        if hasattr(field, 'data'):
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
                screenshot1 = request.files["screenshot1"]
                screenshot2 = request.files["screenshot2"]
                screenshot3 = request.files["screenshot3"]
                screenshot4 = request.files["screenshot4"]
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
                    item.pkg_predepends = tags.get("Pre-Depends", "")
                    item.pkg_conflicts = tags.get("Conflicts", "")
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

                    # Upload screenshot 1
                    ss_base_path = path.join(base_path, "screenshots")
                    sshot_s3_path = generate_bucket_key(ss_base_path,
                                                        "screenshot1",
                                                        screenshot1.filename)
                    _, sshot_tmpfile = mkstemp()
                    with open(sshot_tmpfile, "wb") as tmp:
                        tmp.write(screenshot1.read())
                    upload_to_s3.delay(assets_bucket, sshot_s3_path, sshot_tmpfile, True)

                    # Upload screenshot 2
                    ss_base_path = path.join(base_path, "screenshots")
                    sshot_s3_path = generate_bucket_key(ss_base_path,
                                                        "screenshot2",
                                                        screenshot2.filename)
                    _, sshot_tmpfile = mkstemp()
                    with open(sshot_tmpfile, "wb") as tmp:
                        tmp.write(screenshot2.read())
                    upload_to_s3.delay(assets_bucket, sshot_s3_path, sshot_tmpfile, True)

                    # Upload screenshot 3
                    ss_base_path = path.join(base_path, "screenshots")
                    sshot_s3_path = generate_bucket_key(ss_base_path,
                                                        "screenshot3",
                                                        screenshot3.filename)
                    _, sshot_tmpfile = mkstemp()
                    with open(sshot_tmpfile, "wb") as tmp:
                        tmp.write(screenshot3.read())
                    upload_to_s3.delay(assets_bucket, sshot_s3_path, sshot_tmpfile, True)

                    # Upload screenshot 4
                    ss_base_path = path.join(base_path, "screenshots")
                    sshot_s3_path = generate_bucket_key(ss_base_path,
                                                        "screenshot4",
                                                        screenshot4.filename)
                    _, sshot_tmpfile = mkstemp()
                    with open(sshot_tmpfile, "wb") as tmp:
                        tmp.write(screenshot4.read())
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
imods_admin.add_view(VIPView(db.session))
# imods_admin.add_view(PackageAssetsView(name="Manage Assets"))
