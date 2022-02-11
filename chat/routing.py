from django.urls import path, re_path
from .consumers import ChatsConsumer, ChatConsumer

ws_urlpatterns = [
    path('ws/chat/list/', ChatsConsumer.as_asgi()),
    re_path(r'ws/chat/(?P<chat_id>\w+)/$', ChatConsumer.as_asgi())
]
