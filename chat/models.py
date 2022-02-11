from django.db import models
from django.utils import timezone
from authentication.models import User


# Create your models here.

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
