from core.exceptions import FlamesCLoudException
from rest_framework import status


class AuthException(FlamesCLoudException):
    status_code = status.HTTP_400_BAD_REQUEST


class AuthUserNotFoundException(AuthException):
    status_code = status.HTTP_404_NOT_FOUND
    code = 'user_not_found'
    message = 'User not found'
    fields = ['email']


class AuthProfileNotFoundException(AuthException):
    status_code = status.HTTP_404_NOT_FOUND
    code = 'profile_not_found'
    message = 'Profile not found'
    fields = ['profile']


class AuthInvalidUsernameException(AuthException):
    code = 'username_invalid'
    message = 'The username should only contains alphanumeric characters.'
    fields = ['username']


class AuthInvalidCredentialsException(AuthException):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = 'credentials_invalid'
    message = 'Invalid Credentials, Try again.'


class AuthInvalidTokenException(AuthException):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = 'token_not_valid'
    message = 'Token is invalid or expired.'


class InvalidDataException(AuthException):
    code = 'invalid_data'
    message = 'Data not valid.'
    fields = []


class ProfileAlreadyExists(AuthException):
    status_code = status.HTTP_406_NOT_ACCEPTABLE
    code = 'profile_already_exists'
    message = 'User Profile already exists.'
    fields = ['profile']
