from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone


class UserManager(BaseUserManager):

    def create_user(self, username, email, password=None):
        if not username:
            raise TypeError('User must have username')
        if not email:
            raise TypeError('User must have email')

        user = self.model(username=username, email=self.normalize_email(email))
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, username, email, password=None):
        if not password:
            raise TypeError('User must have password')

        user = self.create_user(username, email, password)
        user.is_superuser = True
        user.is_staff = True
        user.save()
        return user


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=255, unique=True, db_index=True)
    email = models.EmailField(max_length=255, unique=True, db_index=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(default=timezone.now)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    objects = UserManager()

    def __str__(self):
        return f'{self.username}'

    @property
    def tokens(self):
        refresh = RefreshToken.for_user(self)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token)
        }

    @property
    def chats_group(self):
        return f'user.{self.pk}.chats'

    @property
    def active_session(self):
        session = None
        try:
            session = self.sessions.filter(state='ACTIVE').latest('started_at')
        except Session.DoesNotExist:
            pass
        return session

    @property
    def session(self):
        session = None
        try:
            session = self.sessions.latest('started_at')
        except Session.DoesNotExist:
            pass
        return session

    def start_session(self):
        sessions = self.sessions
        for session in sessions.filter(state='ACTIVE'):
            session.end()
        return sessions.create()

    def has_profile(self):
        return hasattr(self, 'profile')


class Profile(models.Model):
    GENDER_OPTIONS = [
        ('MALE', 'MALE'),
        ('FEMALE', 'FEMALE')
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=64, db_index=True)
    last_name = models.CharField(max_length=64, db_index=True)
    gender = models.CharField(choices=GENDER_OPTIONS, max_length=32)
    birthdate = models.DateField()
    country_code = models.CharField(max_length=24, db_index=True)
    device_language = models.CharField(max_length=24, db_index=True)
    quote = models.CharField(max_length=255, null=True, default=None)
    description = models.CharField(max_length=255, null=True, default=None, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    score = models.BigIntegerField(default=0)
    yearly_score = models.IntegerField(default=0)
    monthly_score = models.IntegerField(default=0)
    weekly_score = models.IntegerField(default=0)

    # image = models.ImageField(default='media/images/profile/default.svg')
    # cover = models.ImageField(default='media/images/cover/default.jpg'    )

    def __str__(self):
        return f'{self.user.username} Profile'

    @property
    def latest_image(self):
        return self.media.filter(type='IMAGE').latest('created_at')

    @latest_image.setter
    def latest_image(self, data):
        if data is not None:
            self.temp_latest_image = Media(**data, profile=self)
        else:
            self.temp_latest_image = None

    def save_latest_image(self):
        if self.temp_latest_image is not None:
            self.temp_latest_image.save()

    @property
    def latest_cover(self):
        return self.media.filter(type='COVER').latest('created_at')


class Media(models.Model):
    TYPE_OPTIONS = [
        ('IMAGE', 'IMAGE'),
        ('COVER', 'COVER')
    ]
    profile = models.ForeignKey(to=Profile, on_delete=models.DO_NOTHING, related_name='media')
    media = models.ImageField()
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    name = models.CharField(max_length=255)
    type = models.CharField(choices=TYPE_OPTIONS, max_length=255, db_index=True)
    extension = models.CharField(max_length=24)
    size = models.BigIntegerField()

    class Meta:
        db_table = 'ProfileMedia'
        verbose_name_plural = 'Media'


class Session(models.Model):
    STATE_OPTIONS = [
        ('ACTIVE', 'ACTIVE'),
        ('INACTIVE', 'INACTIVE')
    ]
    user = models.ForeignKey(to=User, on_delete=models.DO_NOTHING, related_name='sessions')
    state = models.CharField(choices=STATE_OPTIONS, default='ACTIVE', max_length=30, db_index=True)
    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    ended_at = models.DateTimeField(default=None, db_index=True, null=True)

    def end(self):
        self.state = 'INACTIVE'
        self.ended_at = timezone.now()
        self.save()
