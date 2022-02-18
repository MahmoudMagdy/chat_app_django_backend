import datetime

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from . import exceptions
from .models import Chat
from .serializers import ChatSerializer, MessageSerializer
from authentication.serializers import ChatUserSerializer
from rest_framework.exceptions import ValidationError
from authentication.exceptions import auth_user_not_found, AuthUserNotFoundException
import asyncio


class ChatsConsumer(AsyncJsonWebsocketConsumer):
    user = None
    chats_group_name = None
    session = None

    async def connect(self):
        await self.accept()
        self.user = self.scope['user']
        # Validating Data
        if self.user.is_anonymous:
            return await self.close(code=auth_user_not_found())
        # Init Session
        self.session = await self.start_user_session()
        self.chats_group_name = self.user.chats_group
        await self.channel_layer.group_add(self.chats_group_name, self.channel_name)

    async def disconnect(self, code):
        if self.chats_group_name:
            await self.channel_layer.group_discard(self.chats_group_name, self.channel_name)
        if self.session:
            await self.end_user_session()

    async def chat_message(self, event):
        chat_id = event['chat_id']
        chat = await self.get_chat_json(chat_id=chat_id)
        await self.send_json(content=chat)

    @database_sync_to_async
    def get_chat_json(self, chat_id):
        chat_json = None
        try:
            serializer = ChatSerializer(instance=self.user.chats.get(pk=chat_id))
            serializer.uid = self.user.pk
            chat_json = serializer.data
        except Chat.DoesNotExist:
            pass
        return chat_json

    @database_sync_to_async
    def start_user_session(self):
        return self.user.start_session(self.channel_name)

    @database_sync_to_async
    def end_user_session(self):
        self.session.end()


# TODO: check if any of the users not in channel group post message some way in there notification channel or
#       something like that.
class ChatConsumer(AsyncJsonWebsocketConsumer):
    user = None
    chat_id = None
    chat = None
    session = None
    is_chat_member = None
    chat_group_name = None

    async def connect(self):
        await self.accept()
        self.user = self.scope['user']
        # Validating Data
        if self.user.is_anonymous:
            return await self.close(code=auth_user_not_found())
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        if not self.chat_id.isnumeric():
            return await self.close(code=exceptions.chat_not_found())
        try:
            self.chat = await self.get_chat(self.chat_id)
        finally:
            if not self.chat:
                return await self.close(code=exceptions.chat_not_found())
        self.is_chat_member = await self.check_chat_member(self.chat, self.user.pk)
        if not self.is_chat_member:
            return await self.close(code=exceptions.unauthoraized_chat_access())
        # Init Session
        try:
            self.session = await self.start_chat_session()
        except AuthUserNotFoundException:
            return await self.close(code=auth_user_not_found())
        self.chat_group_name = f'chat.{self.chat_id}'
        await self.channel_layer.group_add(self.chat_group_name, self.channel_name)

    async def disconnect(self, code):
        if self.chat_group_name:
            await self.channel_layer.group_discard(self.chat_group_name, self.channel_name)
        if self.session:
            await self.end_chat_session()

    async def receive_json(self, content, **kwargs):
        # Double Checking Data (As we need to accept connection to send )
        if not self.is_chat_member:
            return
        try:
            message = await self.create_message(content=content)
        except (ValidationError, Exception):
            return await self.close(code=exceptions.chat_message_invalid())

        await self.channel_layer.group_send(
            self.chat_group_name,
            {
                'type': 'chat_message',
                'message': message
            }
        )
        users_chats_groups = await self.get_users_chats_groups()
        users_notifications_groups = await self.get_users_notifications_groups()
        send_chats = self.forward_to_users_chats(users_chats_groups)
        send_notifications = self.forward_to_users_notifications(users_notifications_groups, message)
        await asyncio.gather(send_chats, send_notifications)

    async def chat_message(self, event):
        message = event['message']
        await self.send_json(content=message)

    async def forward_to_users_chats(self, groups):
        content = {
            'type': 'chat_message',
            'chat_id': self.chat_id,
        }
        for group in groups:
            await self.channel_layer.group_send(group, content)

    async def forward_to_users_notifications(self, groups, message):
        await self.prepare_message_to_notification(message)
        content = {
            'type': 'chat_message',
            'message': message,
        }
        for group in groups:
            await self.channel_layer.group_send(group, content)

    @database_sync_to_async
    def prepare_message_to_notification(self, message):
        del message['chat_id']
        del message['user_id']
        chat_serializer = ChatSerializer(instance=self.chat)
        chat_serializer.uid = self.user.pk
        message['chat'] = chat_serializer.data
        message['user'] = ChatUserSerializer(instance=self.user).data

    @database_sync_to_async
    def get_chat(self, chat_id):
        return Chat.objects.get(pk=chat_id)

    @database_sync_to_async
    def check_chat_member(self, chat, user_id):
        return chat.users.filter(pk=user_id).exists()

    """
        @return chats groups of active users and notifications groups of users that active but not active at any chat or
                active at another chats but not current chat.
    """

    @database_sync_to_async
    def get_users_chats_groups(self):
        active_members = self.chat.users.filter(sessions__state='ACTIVE')
        return [member.chats_group for member in active_members]

    @database_sync_to_async
    def get_users_notifications_groups(self):
        cur_pk = self.user.pk
        active_members = [member for member in self.chat.users.all() if member.notifications_group_active]
        active_members_chats_sessions = [(member, member.active_chats_sessions) for member in active_members]
        return [member.notifications_group for member, sessions in active_members_chats_sessions if
                member.pk != cur_pk and
                (len(sessions) == 0 or self.chat.pk not in [session.chat.pk for session in sessions])]

    @database_sync_to_async
    def create_message(self, content):
        serializer = MessageSerializer(data=content)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=self.user, chat=self.chat)
        return serializer.data

    @database_sync_to_async
    def start_chat_session(self):
        return self.chat.start_session(user=self.user, channel_name=self.channel_name)

    @database_sync_to_async
    def end_chat_session(self):
        self.session.end()
