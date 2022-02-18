from channels.generic.websocket import AsyncJsonWebsocketConsumer
from authentication.exceptions import auth_user_not_found


class NotificationsConsumer(AsyncJsonWebsocketConsumer):
    user = None
    notifications_group_name = None

    async def connect(self):
        await self.accept()
        self.user = self.scope['user']
        # Validating Data
        if self.user.is_anonymous:
            return await self.close(code=auth_user_not_found())
        # Init Session
        await self.start_notification_session()
        self.notifications_group_name = self.user.notifications_group
        await self.channel_layer.group_add(self.notifications_group_name, self.channel_name)

    async def disconnect(self, code):
        if self.notifications_group_name:
            await self.channel_layer.group_discard(self.notifications_group_name, self.channel_name)
            await self.end_notification_session()

    async def chat_message(self, event):
        message = event['message']
        await self.send_json(content={
            'type': 'NEW_MESSAGE',
            'data': message
        })

    async def start_notification_session(self):
        self.user.activate_notifications()

    async def end_notification_session(self):
        self.user.deactivate_notifications()
