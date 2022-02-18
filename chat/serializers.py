from rest_framework import serializers
from .models import Chat, Message
from authentication.serializers import ChatUserSerializer


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'chat_id', 'user_id', 'type', 'content', 'created_at']


class ChatSerializer(serializers.ModelSerializer):
    users = serializers.SerializerMethodField()
    latest_message = MessageSerializer(many=False, read_only=True)

    class Meta:
        model = Chat
        fields = ['id', 'type', 'users', 'created_at', 'updated_at', 'title', 'latest_message']

    user_serializer = ChatUserSerializer
    uid = None

    def get_users(self, obj):
        if not self.uid:
            request = self.context.get('request', {})
            self.uid = request.user.pk

        return list(map(lambda user: self.user_serializer(user).data, obj.users.exclude(id=self.uid)))
