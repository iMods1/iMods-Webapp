import wtforms as wtf
from werkzeug.datastructures import FileStorage
from imods import app


def validate_imgfile(form, field):
    if field.data and isinstance(field.data, FileStorage):
        filename = field.data.filename.lower()

        ALLOWED_EXTENSIONS = app.config["ALLOWED_EXTENSIONS"]
        ext = filename.rsplit('.', 1)
        if not ('.' in filename and ext[1].lower() in ALLOWED_EXTENSIONS):
            raise wtf.validators.ValidationError(
                'Wrong Filetype, you can upload only png,jpg,jpeg files')


def validate_debfile(form, field):
    if field.data and isinstance(field.data, FileStorage):
        filename = field.data.filename.lower()
        ext = filename.rsplit('.', 1)
        if '.' not in filename or ext[1] != "deb":
            raise wtf.validators.ValidationError('You can only '
                                                 'upload deb files')
