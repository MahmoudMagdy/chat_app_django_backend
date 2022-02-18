from django.contrib import admin
from .models import Chat, Message, Session

admin.site.register(Chat)
admin.site.register(Message)
admin.site.register(Session)
