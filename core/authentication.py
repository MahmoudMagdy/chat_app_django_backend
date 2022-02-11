from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from . import exceptions

# For TokenAuthMiddleWare for Websocket
from channels.db import database_sync_to_async
from django.db import close_old_connections
from django.contrib.auth.models import AnonymousUser
from jwt import ExpiredSignatureError, DecodeError, decode as jwt_decode
from django.conf import settings
from django.contrib.auth import get_user_model


class CustomJWTAuthentication(JWTAuthentication):
    def get_validated_token(self, raw_token):
        try:
            return super(CustomJWTAuthentication, self).get_validated_token(raw_token)
        except InvalidToken:
            raise exceptions.NotAuthenticatedToken

    def get_user(self, validated_token):
        try:
            return super(CustomJWTAuthentication, self).get_user(validated_token)
        except AuthenticationFailed as error:
            if error.detail['code'] == 'user_not_found':
                raise exceptions.NotAuthenticatedToken
            elif error.detail['code'] == 'user_inactive':
                raise exceptions.AuthUserDisabled
            else:
                raise error


@database_sync_to_async
def get_user(user_id):
    user_cls = get_user_model()
    try:
        return user_cls.objects.get(id=user_id)
    # Over Exception Handling -> as if token is okay for sure user_id is correct
    except user_cls.DoesNotExist:
        # I am leaving it as it's to make it translatable in future
        msg = 'User Does Not Exist.'
        raise AuthenticationFailed(msg)


class TokenAuthMiddleware:
    """
    Custom token auth middleware
    """

    def __init__(self, app):
        # Store the ASGI application we were passed
        self.app = app

    async def __call__(self, scope, receive, send):

        # Close old database connections to prevent usage of timed out connections
        close_old_connections()

        # Get Headers and Convert it from List of Sets key and value => [(k0,v0),(k1,v1)] to  dict
        headers = dict(scope['headers'])
        if b'authorization' in headers:
            try:
                scope['user'] = await self.authenticate_credentials(headers[b'authorization'])
            except (AuthenticationFailed, Exception) as e:
                scope['user'] = AnonymousUser()
        else:
            scope['user'] = AnonymousUser()
        # Return the application directly and let it run everything else
        return await self.app(scope, receive, send)

    @staticmethod
    async def authenticate_credentials(payload):
        # bytes = b'...' literals = a sequence of octets (integers between 0 and 255)
        # Convert Bytes String to String
        try:
            token_name, token_key = payload.decode().split()
        except ValueError:
            msg = 'Invalid Auth Type.'
            raise AuthenticationFailed(msg)
        else:
            if token_name == 'Bearer':
                # Try to authenticate the user
                try:
                    # This will automatically validate the token and raise an error if token is invalid
                    # jwt.decode as jwt_decode
                    decoded_data = jwt_decode(token_key, settings.SECRET_KEY, algorithms=["HS256"])
                    # Will return a dictionary like -
                    # {
                    #   'token_type': 'access',
                    #   'exp': 1643494795,
                    #   'iat': 1643408395,
                    #   'jti': '25d804e168a3412e8c0b29d12dcd7645',
                    #   'user_id': 1
                    # }
                    # Then token is valid
                    # Get the user using ID
                    user = await get_user(user_id=decoded_data["user_id"])
                    if not user.is_active:
                        msg = 'User account is disabled.'
                        raise AuthenticationFailed(msg)
                except ExpiredSignatureError:
                    msg = 'Token Expired.'
                    raise AuthenticationFailed(msg)
                except DecodeError:
                    msg = 'Invalid Token.'
                    raise AuthenticationFailed(msg)
            else:
                msg = 'Invalid Auth Type.'
                raise AuthenticationFailed(msg)
            return user
