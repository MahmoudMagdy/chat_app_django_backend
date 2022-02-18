from django.db import models
from django.utils import timezone
from authentication.models import User
from authentication.exceptions import AuthUserNotFoundException


class Chat(models.Model):
    TYPE_OPTIONS = [
        ('CONVERSATION', 'CONVERSATION'),
        ('ROOM', 'ROOM'),
    ]

    type = models.CharField(choices=TYPE_OPTIONS, max_length=20)
    users = models.ManyToManyField(User, related_name='chats')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    title = models.CharField(max_length=100, default=None, null=True)

    @property
    def latest_message(self):
        return self.messages.latest('created_at')

    def start_session(self, user, channel_name):
        if not isinstance(user, User):
            raise AuthUserNotFoundException()
        sessions = self.sessions
        for session in sessions.filter(user=user, state='ACTIVE'):
            session.end()
        return sessions.create(user=user, channel_name=channel_name)


class Message(models.Model):
    TYPE_OPTIONS = [
        ('TEXT', 'TEXT'),
        ('IMAGE', 'IMAGE'),
        ('VOICE', 'VOICE'),
        ('AUDIO', 'AUDIO'),
        ('VIDEOS', 'VIDEOS'),
        ('DOCUMENT', 'DOCUMENT'),
        ('ATTACHMENT', 'ATTACHMENT'),
    ]

    user = models.ForeignKey(to=User, on_delete=models.DO_NOTHING, related_name='messages')
    chat = models.ForeignKey(to=Chat, on_delete=models.DO_NOTHING, related_name='messages')
    type = models.CharField(choices=TYPE_OPTIONS, max_length=20)
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    is_disabled = models.BooleanField(default=False)


class Session(models.Model):
    STATE_OPTIONS = [
        ('ACTIVE', 'ACTIVE'),
        ('INACTIVE', 'INACTIVE')
    ]

    user = models.ForeignKey(to=User, on_delete=models.DO_NOTHING, related_name='chats_sessions')
    chat = models.ForeignKey(to=Chat, on_delete=models.DO_NOTHING, related_name='sessions')
    state = models.CharField(choices=STATE_OPTIONS, default='ACTIVE', max_length=30, db_index=True)
    channel_name = models.CharField(max_length=255)
    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    ended_at = models.DateTimeField(default=None, db_index=True, null=True)

    def end(self):
        self.state = 'INACTIVE'
        self.ended_at = timezone.now()
        self.save()
