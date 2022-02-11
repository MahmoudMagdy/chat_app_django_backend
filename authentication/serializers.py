from rest_framework import serializers
from .models import User, Profile, Media, Session
from django.contrib import auth
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import smart_bytes, force_str, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from .utils import MailingUtils
from . import exceptions
import re
from django.utils import timezone
from core.exceptions import AuthUserDisabled

# make a pattern
pattern = "^[A-Za-z0-9_]*$"


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(max_length=68, min_length=6, write_only=True)
    id = serializers.IntegerField(read_only=True)
    is_verified = serializers.BooleanField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    is_staff = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    last_login = serializers.DateTimeField(read_only=True)
    tokens = serializers.JSONField(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'username', 'is_verified', 'is_active', 'is_staff', 'created_at',
                  'updated_at', 'last_login', 'tokens']

    def validate(self, attrs):
        username = attrs.get('username', '')
        if not bool(re.match(pattern, username)):
            raise exceptions.AuthInvalidUsernameException()
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'is_verified', 'is_active', 'is_staff', 'created_at', 'updated_at']


class MediaSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    media = serializers.CharField()

    class Meta:
        model = Media
        fields = ['id', 'media', 'name', 'type', 'extension', 'size', 'created_at', 'profile_id']

    def to_representation(self, obj):
        self.fields['media'] = serializers.ImageField()
        return super().to_representation(obj)


class CreateProfileSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    user = UserSerializer(many=False, read_only=True)
    quote = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    latest_image = MediaSerializer(many=False, default=None, allow_null=True)
    latest_cover = MediaSerializer(many=False, read_only=True)

    class Meta:
        model = Profile
        fields = ('id', 'user', 'first_name', 'last_name', 'country_code', 'device_language', 'gender', 'birthdate',
                  'quote', 'description', 'created_at', 'updated_at', 'latest_image', 'latest_cover', 'user_id')


class ProfileSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    latest_image = MediaSerializer(many=False, read_only=True)
    latest_cover = MediaSerializer(many=False, read_only=True)

    class Meta:
        model = Profile
        fields = ('id', 'first_name', 'last_name', 'country_code', 'device_language', 'gender', 'birthdate',
                  'quote', 'description', 'created_at', 'updated_at', 'latest_image', 'latest_cover', 'user_id')


class LoginSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    email = serializers.EmailField(max_length=255, min_length=5)
    password = serializers.CharField(max_length=68, min_length=6, write_only=True)
    username = serializers.CharField(max_length=255, read_only=True)
    tokens = serializers.JSONField(read_only=True)
    is_verified = serializers.BooleanField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    is_staff = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    last_login = serializers.DateTimeField(read_only=True)
    profile = ProfileSerializer(many=False, required=False, read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'username', 'is_verified', 'is_active', 'is_staff', 'created_at',
                  'updated_at', 'last_login', 'tokens', 'profile']

    def validate(self, attrs):
        email = attrs.get('email', '')
        password = attrs.get('password', '')
        user = auth.authenticate(email=email, password=password)
        if not user:
            if not User.objects.filter(email=email).exists():
                raise exceptions.AuthUserNotFoundException()
            user_data = User.objects.get(email=email)
            if user_data.check_password(password) and not user_data.is_active:
                raise AuthUserDisabled()
            raise exceptions.AuthInvalidCredentialsException()
        user.last_login = timezone.now()
        user.save()
        return user


class ResetPasswordRequestSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length=255, min_length=5)

    class Meta:
        model = User
        fields = ['email']

    def validate(self, attrs):
        request = self.context.get('request', {})
        email = attrs.get('email', '')
        if not User.objects.filter(email=email).exists():
            raise exceptions.AuthUserNotFoundException()
        user = User.objects.get(email=email)
        if not user.is_active:
            raise AuthUserDisabled()
        uidb64 = urlsafe_base64_encode(smart_bytes(user.pk))
        token = PasswordResetTokenGenerator().make_token(user)
        current_site = get_current_site(request).domain
        relative_link = reverse('auth_reset_password_confirm', kwargs={'uidb64': uidb64, 'token': token})
        abs_url = f'http://{current_site}{relative_link}'
        data = {
            'subject': 'Reset your password for FlamesCloud',
            'body': f'Hello,Follow this link to reset your FlamesCloud password for your {email} account.\n'
                    f'{abs_url}\n'
                    f'If you didn’t ask to reset your password, you can ignore this email.\n'
                    f'Thanks,\n'
                    f'Your FlamesCloud team',
            'to': [user.email]
        }
        MailingUtils.send_email(data)
        return attrs


class RestPasswordSerializer(serializers.ModelSerializer):
    password = serializers.CharField(max_length=68, min_length=6, write_only=True)
    token = serializers.CharField(min_length=1, write_only=True)
    uidb64 = serializers.CharField(min_length=1, write_only=True)

    class Meta:
        model = User
        fields = ['password', 'token', 'uidb64']

    def validate(self, attrs):
        try:
            password = attrs.get('password')
            token = attrs.get('token')
            uidb64 = attrs.get('uidb64')
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(id=uid)
            if not PasswordResetTokenGenerator().check_token(user, token):
                raise AuthenticationFailed('Reset link expired')
            user.set_password(password)
            user.save()
            return user
        except (DjangoUnicodeDecodeError, User.DoesNotExist):
            raise AuthenticationFailed('Reset link is invalid')


# Serializers for `Chat` app
class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = ['state', 'started_at', 'ended_at']


class ChatUserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(many=False, read_only=True)
    session = SessionSerializer(many=False, read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'is_verified', 'is_active', 'is_staff', 'created_at',
                  'updated_at', 'last_login', 'profile', 'session']
