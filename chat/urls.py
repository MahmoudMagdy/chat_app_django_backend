from django.urls import path
from . import views

urlpatterns = [
    path('list/', views.ChatListApiView.as_view(), name='chat_list'),
    path('detail/', views.ChatDetailAPIView.as_view(), name='chat_item'),
    path('create/<oid>/', views.ChatConversationCreateAPIView.as_view(), name='chat_conversation_create'),
    path('<pk>/', views.ChatMessageListApiView.as_view(), name='chat_message_list'),
]
