from rest_framework.permissions import BasePermission
from .models import Chat
from enum import Enum


class PermissionCode(Enum):
    NO_CHAT_WITH_ID = 'no_chat_with_id'
    NOT_CHAT_MEMBER = 'not_chat_member'


class IsChatMember(BasePermission):
    code = None

    def has_permission(self, request, view):
        chat_id = view.kwargs['pk']
        try:
            chat = Chat.objects.get(pk=chat_id)
        except Chat.DoesNotExist:
            self.code = PermissionCode.NO_CHAT_WITH_ID
            return False
        if not chat.users.filter(pk=request.user.pk).exists():
            self.code = PermissionCode.NOT_CHAT_MEMBER
            return False
        view.chat = chat
        return True
