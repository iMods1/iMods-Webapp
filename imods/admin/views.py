from imods import db, app
from imods.models import User, BillingInfo, Category, Device, Item, Order
from imods.models import UserRole, BillingType, OrderStatus, Review
from imods.helpers import db_scoped_session, generate_bucket_key
from flask.ext.admin import Admin, expose, helpers, AdminIndexView, BaseView
from flask.ext.admin.contrib.sqla import ModelView
from flask import session, redirect, url_for, request, render_template
from werkzeug import check_password_hash, generate_password_hash
import wtforms as wtf
from flask.ext.wtf import Form as ExtForm
import boto
import os

def checkfile(form, field):
    if field.data:
        filename=field.data.name.lower()

        ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg',
                                                'gif'])
        if not ('.' in filename and filename.rsplit('.',1)[1] in ALLOWED_EXTENSIONS):
            raise ValidationError('Wrong Filetype, you can upload only png,jpg,jpeg,gif files')
        else:
            raise ValidationError('field not Present')

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

class PackageAssetsUploadForm(ExtForm):
    item_id = wtf.fields.SelectField(u"Item", coerce=int)
    app_icon = wtf.fields.FileField(u"App Icon", validators=[checkfile])
    screenshot = wtf.fields.FileField(u"Screenshot", validators=[checkfile])

class iModsAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if not session.get('user'):
            return redirect(url_for('.login_view'))
        elif session['user']['role'] != UserRole.SiteAdmin:
            raise wtf.validators.ValidationError(
                "You don't have required permission to access this page.")
        return super(iModsAdminIndexView, self).index()

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

class PackageAssetsView(BaseView):
    template_name = u"package_assets.html"

    @expose('/', methods=["GET", "POST"])
    def index(self):

        form = PackageAssetsUploadForm(request.form)

        # Populate choices for select field
        with db_scoped_session() as s:
            items = s.query(Item).all()
            form.item_id.choices = [(item.iid, item.display_name)
                                                for item in items]

            if helpers.validate_form_on_submit(form):
                from boto.s3.key import Key
                # Get file data from request.files
                app_icon = request.files["app_icon"]
                screenshot = request.files["screenshot"]
                # Get pkg_assets_path
                item = s.query(Item).get(form.item_id.data)
                base_path = item.pkg_assets_path

                # Connect to S3 Bucket
                s3 = boto.connect_s3(profile_name=app.config.get("BOTO_PROFILE"))
                bucket = s3.get_bucket('imods_package')

                # Upload icon
                icon = bucket.new_key(generate_bucket_key(base_path, "app_icon",
                                        app_icon.filename))
                icon.set_contents_from_string(app_icon.read())

                # Upload screenshot
                sshot = bucket.new_key(generate_bucket_key(base_path,
                                        "screenshot",
                                        screenshot.filename))
                sshot.set_contents_from_string(screenshot.read())

                return redirect(url_for('admin.index'))


        context = { 'form': form }
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

