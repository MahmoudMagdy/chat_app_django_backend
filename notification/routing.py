from django.urls import path
from .consumers import NotificationsConsumer

notification_ws_urlpatterns = [
    path('ws/notification/list/', NotificationsConsumer.as_asgi()),
]
