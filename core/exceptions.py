from rest_framework.exceptions import APIException
from rest_framework import status


class FlamesCLoudException(APIException):
    code = 'error'
    message = 'Error occurred'
    fields = []
    additional_detail = None

    def __init__(self):
        detail = [{
            'code': self.code,
            'message': self.message,
            'fields': self.fields,
            'status_code': self.status_code
        }]
        if self.additional_detail is not None:
            detail = detail[0] | self.additional_detail
        super().__init__(detail, self.code)

    def __add__(self, other):
        if type(self) == EmptyException:
            return other
        if isinstance(other, FlamesCLoudException):
            self.detail += other.detail
            self.fields += other.fields
            self.status_code = self.status_code if self.status_code > other.status_code else other.status_code
            self.code = 'error'
            self.message = 'Error occurred'
            self.additional_detail = None
        else:
            NotImplemented
        return self

    def __iadd__(self, other):
        if type(self) == EmptyException:
            return other
        elif isinstance(other, FlamesCLoudException):
            self.detail += other.detail
            self.fields += other.fields
            self.status_code = self.status_code if self.status_code > other.status_code else other.status_code
            self.code = 'error'
            self.message = 'Error occurred'
            self.additional_detail = None
        else:
            NotImplemented
        return self


class EmptyException(FlamesCLoudException):
    code = None
    message = None
    fields = None
    additional_detail = None


class NotAuthenticatedRequest(FlamesCLoudException):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = 'not_authenticated'
    message = 'Authentication credentials were not provided.'
    auth_header = 'Bearer realm="api"'


class NotAuthenticatedToken(FlamesCLoudException):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = 'token_invalid_expired'
    message = 'Token is invalid or expired.'
    fields = ['AccessToken']
    auth_header = 'Bearer realm="api"'


class AuthUserDisabled(FlamesCLoudException):
    status_code = status.HTTP_403_FORBIDDEN
    code = 'user_disabled'
    message = 'User disabled'
    auth_header = 'Bearer realm="api"'


class ValidationException(FlamesCLoudException):
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, code, field, message):
        self.code = f'{field}_{code}'
        self.message = message
        self.fields = [field]
        FlamesCLoudException.__init__(self)


def validation_exceptions(error):
    errors = EmptyException()
    for key in error.detail:
        error_item = error.detail[key][0]
        error_code = error_item.code
        error_message = str(error_item)
        errors += ValidationException(error_code, key, error_message)
    return errors
