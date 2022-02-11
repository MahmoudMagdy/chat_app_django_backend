from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from . import exceptions
from .models import Chat
from .serializers import ChatSerializer, MessageSerializer
from rest_framework.exceptions import ValidationError


# TODO: check what will happen if i sent to group that doesn't exist in redis memory
class ChatsConsumer(AsyncJsonWebsocketConsumer):
    user = None
    session = None
    chats_group_name = None

    async def connect(self):
        await self.accept()
        self.user = self.scope['user']
        # Validating Data
        if self.user.is_anonymous:
            return await self.close(code=exceptions.auth_user_not_found())
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
    def start_user_session(self):
        return self.user.start_session()

    @database_sync_to_async
    def end_user_session(self):
        self.session.end()

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


# TODO: check if any of the users not in channel group post message some way in there notification channel or
#       something like that.
class ChatConsumer(AsyncJsonWebsocketConsumer):
    user = None
    chat_id = None
    chat = None
    is_chat_member = None
    chat_group_name = None

    async def connect(self):
        await self.accept()
        self.user = self.scope['user']
        # Validating Data
        if self.user.is_anonymous:
            return await self.close(code=exceptions.auth_user_not_found())
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
        self.chat_group_name = f'chat_{self.chat_id}'
        await self.channel_layer.group_add(self.chat_group_name, self.channel_name)

    async def disconnect(self, code):
        if self.chat_group_name:
            await self.channel_layer.group_discard(self.chat_group_name, self.channel_name)

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
        await self.forward_to_users_chats(users_chats_groups)

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

    @database_sync_to_async
    def get_chat(self, chat_id):
        return Chat.objects.get(pk=chat_id)

    @database_sync_to_async
    def check_chat_member(self, chat, user_id):
        return chat.users.filter(pk=user_id).exists()

    @database_sync_to_async
    def get_users_chats_groups(self):
        members = self.chat.users.all()
        return [member.chats_group for member in filter(lambda member: member.active_session, members)]

    @database_sync_to_async
    def create_message(self, content):
        serializer = MessageSerializer(data=content)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=self.user, chat=self.chat)
        return serializer.data
