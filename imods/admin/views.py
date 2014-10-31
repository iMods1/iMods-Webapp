from imods import db, app
from imods.models import User, BillingInfo, Category, Device, Item, Order
from imods.models import UserRole, BillingType, OrderStatus, Review
from imods.helpers import db_scoped_session, generate_bucket_key, detect_tweak
from imods.tasks.dpkg import dpkg_update_index, upload_to_s3
from flask.ext.admin import Admin, expose, helpers, AdminIndexView, BaseView
from flask.ext.admin.contrib.sqla import ModelView
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
        return form_class

    def on_model_change(self, form, model, is_created):
        if is_created:
            model.password = generate_password_hash(form.password.data)
        else:
            model.new_password = generate_password_hash(form.new_password.data)

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
                "You don't have required permission to access this page.")

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
    package_file = wtf.fields.FileField(u'Package file(deb)')

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
                # Get pkg_assets_path
                item = s.query(Item).get(form.item_id.data)
                pkg_fullname = item.pkg_name + '-' + str(item.pkg_version)
                base_path = path.join(
                    "packages",
                    item.pkg_name,
                    pkg_fullname,
                    'assets')
                item.pkg_assets_path = base_path

                # Get package file
                package_file = request.files["package_file"]

                _, debTmpFile = mkstemp()
                with open(debTmpFile, "wb") as local_deb_file:
                    local_deb_file.write(package_file.read())

                # Verify and update item information based on package file
                deb_obj = debfile.DebPackage(debTmpFile)
                item.control = deb_obj.control_content("control")
                tags = TagSection(item.control)
                item.dependencies = tags.get("Depends", "")
                pkg_name = tags.get("Package", None)

                try:
                    if (pkg_name is not None) and pkg_name != item.pkg_name:
                        # Check if the name already exists
                        t_item = s.query(Item).filter_by(pkg_name=pkg_name).first()
                        if t_item is None or t_item.iid == item.iid:
                            item.pkg_name = pkg_name
                        else:
                            flash("Package name '%s' is used by another item(%d)."
                                    % (pkg_name, t_item.iid))
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
                        app.config["UPLOAD_PATH"],
                        pkg_s3_key_path)

                    # Local package path
                    pkg_local_cache_dir = path.dirname(pkg_local_cache_path)
                    if not path.exists(pkg_local_cache_dir):
                        print("Creating path %s" % pkg_local_cache_dir)
                        os.makedirs(pkg_local_cache_dir)

                    # Move tmp deb file to the cache folder
                    shutil.move(debTmpFile, pkg_local_cache_path)

                    pkg_overrides = [(item.pkg_name, "itemid", item.iid),
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
                    pkg_index_file = path.join(app.config["UPLOAD_PATH"],
                                               app.config["PKG_INDEX_FILE_NAME"]
                                               )
                    # Update and upload package index
                    dpkg_update_index.delay(app.config["UPLOAD_PATH"],
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
imods_admin.add_view(OrderView(db.session))
imods_admin.add_view(ReviewView(db.session))
imods_admin.add_view(PackageAssetsView(name="Manage Assets"))
