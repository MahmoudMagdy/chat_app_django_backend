import uuid
import jwt
from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.utils.encoding import smart_str, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_decode
from rest_framework import permissions
from rest_framework import status
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.exceptions import ErrorDetail, ValidationError
from core.exceptions import validation_exceptions
from . import exceptions
from .models import User
from core.renderers import StandardRenderer
from . import serializers
from .utils import MailingUtils
from core.s3 import S3
from rest_framework.exceptions import NotAuthenticated
from core.exceptions import NotAuthenticatedRequest
from rest_framework.filters import SearchFilter
from core.permissions import HasProfile


class RegisterAPIView(GenericAPIView):
    serializer_class = serializers.RegisterSerializer
    renderer_classes = (StandardRenderer,)

    def post(self, request):
        user_request = request.data
        self.get_serializer_context()
        serializer = self.serializer_class(data=user_request)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as exception:
            raise validation_exceptions(exception)
        user = serializer.save()

        token = user.tokens['access']

        current_site = get_current_site(request).domain
        relative_link = reverse('auth_verify_email')
        abs_url = f'http://{current_site}{relative_link}?token={token}'
        data = {
            'subject': 'Verify your email for FlamesCloud',
            'body': f'Hello {user.username},\nFollow this link to verify your email address.\n'
                    f'{abs_url}\n'
                    f'If you didn’t ask to verify this address, you can ignore this email.\n'
                    f'Thanks,\n'
                    f'Your FlamesCloud team',
            'to': [user.email]
        }

        MailingUtils.send_email(data)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class VerifyEmailAPIView(GenericAPIView):
    renderer_classes = (StandardRenderer,)

    def get(self, request):
        token = request.GET.get('token')
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            user = User.objects.get(id=payload['user_id'])
            if not user.is_verified:
                user.is_verified = True
                user.save()
            return Response({'email': 'Successfully activated'}, status=status.HTTP_200_OK)
        except jwt.ExpiredSignatureError:
            return Response({'token': ErrorDetail(string='Activation link expired', code='invalid-token')},
                            status=status.HTTP_400_BAD_REQUEST)
        except jwt.DecodeError:
            return Response({'token': ErrorDetail(string='Invalid Token', code='invalid-token')},
                            status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({'data': ErrorDetail(string='Invalid Data', code='invalid-data')},
                            status=status.HTTP_400_BAD_REQUEST)


class LoginAPIView(GenericAPIView):
    serializer_class = serializers.LoginSerializer
    renderer_classes = (StandardRenderer,)

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as exception:
            raise validation_exceptions(exception)

        return Response(serializer.data, status=status.HTTP_200_OK)


class ResetPasswordRequestAPIView(GenericAPIView):
    serializer_class = serializers.ResetPasswordRequestSerializer
    renderer_classes = (StandardRenderer,)

    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as exception:
            raise validation_exceptions(exception)

        return Response({'success': 'A link to reset your password was sent to you'}, status=status.HTTP_200_OK)


class ResetPasswordTokenCheckAPIView(GenericAPIView):
    renderer_classes = (StandardRenderer,)

    def get(self, request, uidb64, token):
        try:
            uid = smart_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(id=uid)
            if not PasswordResetTokenGenerator().check_token(user, token):
                return Response({'token': ErrorDetail(string='Reset link expired', code='invalid-token')},
                                status=status.HTTP_401_UNAUTHORIZED)
            return Response({'success': True, 'message': 'Credential Valid', 'uidb64': uidb64, 'token': token},
                            status=status.HTTP_200_OK)
        except (DjangoUnicodeDecodeError, User.DoesNotExist):
            return Response({'uid': ErrorDetail(string='Reset link is invalid', code='invalid-uid')},
                            status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordAPIView(GenericAPIView):
    renderer_classes = (StandardRenderer,)
    serializer_class = serializers.RestPasswordSerializer

    def patch(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({'success': True, 'message': 'Password reset success'}, status=status.HTTP_200_OK)


class GenerateProfileUrl(GenericAPIView):
    renderer_classes = (StandardRenderer,)
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        data = request.data
        file_type = data.get('type')
        file_size = data.get('size')
        file_extension = data.get('extension')

        if file_type not in ['IMAGE', 'COVER'] or file_extension is None or file_size is None:
            raise exceptions.InvalidDataException()

        if file_type == 'IMAGE':
            path = 'media/images/profile'
        else:
            path = 'media/images/cover'

        file_name = f'{uuid.uuid4().hex}.{file_extension}'
        cloud_path = f'{path}/{file_name}'
        response = S3().get_presigned_post(cloud_path)
        response['cloud_path'] = cloud_path
        return Response(response, status=status.HTTP_200_OK)

    def permission_denied(self, request, message=None, code=None):
        try:
            super(GenerateProfileUrl, self).permission_denied(request, message, code)
        except NotAuthenticated:
            raise NotAuthenticatedRequest


class CreateProfileAPIView(GenericAPIView):
    renderer_classes = (StandardRenderer,)
    serializer_class = serializers.CreateProfileSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as exception:
            raise validation_exceptions(exception)
        if self.request.user.has_profile():
            raise exceptions.ProfileAlreadyExists()
        profile = serializer.save(user=self.request.user)
        profile.save_latest_image()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def permission_denied(self, request, message=None, code=None):
        try:
            super(CreateProfileAPIView, self).permission_denied(request, message, code)
        except NotAuthenticated:
            raise NotAuthenticatedRequest


class TokenRefreshAPIView(TokenRefreshView):
    renderer_classes = (StandardRenderer,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError:
            raise exceptions.AuthInvalidTokenException()
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class CurrentProfileAPIView(GenericAPIView):
    renderer_classes = [StandardRenderer]
    permission_classes = (permissions.IsAuthenticated, HasProfile)
    serializer_class = serializers.CreateProfileSerializer

    def get(self, request):
        user = request.user
        """
            I commented it as checking if user active or not occurs on core.authentication.CustomJWTAuthentication
        """
        # if not user.is_active:
        #     raise AuthUserDisabled()
        serializer = self.serializer_class(user.profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def permission_denied(self, request, message=None, code=None):
        try:
            super(CurrentProfileAPIView, self).permission_denied(request, message, code)
        except NotAuthenticated:
            raise NotAuthenticatedRequest
        except Exception as error:
            if code == HasProfile.code:
                raise exceptions.AuthProfileNotFoundException()
            else:
                raise error


class UserDetailAPIView(GenericAPIView):
    renderer_classes = [StandardRenderer]
    permission_classes = (permissions.IsAuthenticated, HasProfile)
    serializer_class = serializers.ChatUserSerializer

    def get(self, request, uid):
        try:
            user = User.objects.get(pk=uid)
        except User.DoesNotExist:
            raise exceptions.AuthUserNotFoundException()
        serializer = self.serializer_class(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def permission_denied(self, request, message=None, code=None):
        try:
            super(UserDetailAPIView, self).permission_denied(request, message, code)
        except NotAuthenticated:
            raise NotAuthenticatedRequest
        except Exception as error:
            if code == HasProfile.code:
                raise exceptions.AuthProfileNotFoundException()
            else:
                raise error


# TODO: use @ when moving to Postgre db
class UsersListAPIView(ListAPIView):
    serializer_class = serializers.ChatUserSerializer
    queryset = User.objects.all()
    renderer_classes = (StandardRenderer,)
    permission_classes = [permissions.IsAuthenticated, HasProfile]
    filter_backends = [SearchFilter]
    search_fields = ['profile__first_name', 'profile__last_name', 'username',
                     'profile__quote', 'profile__description', '=email',
                     'profile__media__name']

    def permission_denied(self, request, message=None, code=None):
        try:
            super(UsersListAPIView, self).permission_denied(request, message, code)
        except NotAuthenticated:
            raise NotAuthenticatedRequest()
        except Exception as error:
            if code == HasProfile.code:
                raise exceptions.AuthProfileNotFoundException()
            else:
                raise error
