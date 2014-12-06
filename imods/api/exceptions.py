from flask import jsonify


class APIException(Exception):
    status_code = 400

    def __init__(self, message=None, status_code=None, payload=None):
        super(APIException, self).__init__()
        if message is not None:
            self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        rv['status_code'] = self.status_code
        return rv


class InternalException(APIException):
    status_code = 500
    message = "InternalException"


def setup_api_exceptions(app):
    @app.errorhandler(APIException)
    def error_handler_in_json(exp):
        """
        Create Json-Oriented blueprint
        All error responses that you don't specifically
        manage yourself will have application/json content
        type, and will contain JSON like this (just an example):

        { "message": "405: Method Not Allowed" }
        """
        response = jsonify(exp.to_dict())
        response.status_code = (exp.status_code
                                if not isinstance(exp, InternalException)
                                else 500)
        return response


# Client errors
class UserNotLoggedIn(APIException):
    status_code = 403
    message = 'User login required'


class UserAlreadRegistered(APIException):
    status_code = 409
    message = 'User already registered'


class ResourceUniqueError(APIException):
    status_code = 409
    message = 'Unique resource is already inserted'


class CategoryNameReserved(APIException):
    status_code = 409
    message = 'Category name is reserved'


class UserCredentialsDontMatch(APIException):
    status_code = 401
    message = 'Invalid email and password combination.'


class BadJSONData(APIException):
    status_code = 400
    message = 'Json parse error: malformed data'


class BadFormData(APIException):
    status_code = 400
    message = 'Form parse error: malformed data'


class BadURLRequest(APIException):
    status_code = 400
    message = 'Bad URL Request, check parameters'


class UserNotFound(APIException):
    status_code = 404
    message = 'User not found'


class ResourceIDNotFound(APIException):
    status_code = 404
    message = 'Recource ID is not found'


class InvalidToken(APIException):
    status_code = 403
    message = 'Token is not valid'


class InsufficientPrivileges(APIException):
    status_code = 405
    message = 'Not authenticated to perform this operation.'


class CardCreationFailed(APIException):
    status_code = 400
    message = 'There was a problem to add your credit card.'


class CategoryNotEmpty(APIException):
    status_code = 409
    message = 'Category is not empty:The category to delete has one or more \
sub-categories or items,\
please delete all sub-categories and items before deletion.'


class OrderNotChangable(APIException):
    status_code = 401
    message = 'Completed or cancelled orders cannot be changed.'


class CategorySelfParent(APIException):
    status_code = 409
    message = "Category's parent cannot be itself."


class PaymentAuthorizationFailed(APIException):
    status_code = 417
    message = "Payment gateway has refused to authorize the payment."
