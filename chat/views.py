from rest_framework.generics import ListAPIView, GenericAPIView
from rest_framework import permissions
from core.renderers import StandardRenderer
from .serializers import ChatSerializer, MessageSerializer
from rest_framework.exceptions import NotAuthenticated
from core.exceptions import NotAuthenticatedRequest
from . import exceptions
from authentication.exceptions import AuthProfileNotFoundException
from .permissions import IsChatMember, PermissionCode
from core.permissions import HasProfile
from .models import Chat
from authentication.models import User
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from core.exceptions import validation_exceptions


class ChatListApiView(ListAPIView):
    serializer_class = ChatSerializer
    renderer_classes = (StandardRenderer,)
    permission_classes = (permissions.IsAuthenticated, HasProfile)
    pagination_class = None

    def get_queryset(self):
        return self.request.user.chats.all().order_by('updated_at')

    def permission_denied(self, request, message=None, code=None):
        try:
            super(ChatListApiView, self).permission_denied(request, message, code)
        except NotAuthenticated:
            raise NotAuthenticatedRequest()
        except Exception as error:
            if code == HasProfile.code:
                raise AuthProfileNotFoundException()
            else:
                raise error


class ChatMessageListApiView(ListAPIView):
    serializer_class = MessageSerializer
    renderer_classes = (StandardRenderer,)
    permission_classes = [permissions.IsAuthenticated, IsChatMember, HasProfile]

    def get_queryset(self):
        return self.chat.messages.filter(is_disabled=False).order_by('-created_at')

    def permission_denied(self, request, message=None, code=None):
        try:
            super(ChatMessageListApiView, self).permission_denied(request, message, code)
        except NotAuthenticated:
            raise NotAuthenticatedRequest()
        except Exception as error:
            if code == PermissionCode.NO_CHAT_WITH_ID:
                raise exceptions.NoChatWithId()
            elif code == PermissionCode.NOT_CHAT_MEMBER:
                raise exceptions.NotChatMember()
            elif code == HasProfile.code:
                raise AuthProfileNotFoundException()
            else:
                raise error

    """
        Tried to use this method to set Headers 'WWW-Authenticate' but i have found
        that through source code it's easy to be done using 'auth_header' static property
        in exception class.
    """
    # def handle_exception(self, exc):
    #     if isinstance(exc, NotAuthenticatedRequest):
    #         self.headers['WWW-Authenticate'] = 'Bearer realm="api"'
    #     return super(ChatMessageListApiView, self).handle_exception(exc)


class ChatDetailAPIView(GenericAPIView):
    renderer_classes = [StandardRenderer]
    permission_classes = (permissions.IsAuthenticated, HasProfile)
    serializer_class = ChatSerializer

    def get(self, request):
        _id = request.GET.get('_id')
        uid = request.GET.get('uid')
        if not _id and not uid:
            raise exceptions.NoChatRequested()
        user = request.user
        if _id:
            try:
                chat = user.chats.get(pk=_id)
            except Chat.DoesNotExist:
                raise exceptions.NoChatWithId()
        else:
            if int(uid) == user.pk:
                raise exceptions.ChattingSelfNotPermitted()
            try:
                other_user = User.objects.get(pk=uid)
            except User.DoesNotExist:
                raise exceptions.NoChatUserWithId()
            chats = user.chats.filter(type='CONVERSATION')
            if not chats.exists():
                raise exceptions.NoChatMatched()
            chat = None
            """
                Not the correct way but i am gonna handle it later
            """
            for item in chats:
                if other_user in item.users.all():
                    chat = item
                    break
            if not chat:
                raise exceptions.NoChatMatched()
        serializer = self.serializer_class(chat)
        serializer.uid = user.pk
        return Response(serializer.data, status=status.HTTP_200_OK)

    def permission_denied(self, request, message=None, code=None):
        try:
            super(ChatDetailAPIView, self).permission_denied(request, message, code)
        except NotAuthenticated:
            raise NotAuthenticatedRequest
        except Exception as error:
            if code == HasProfile.code:
                raise AuthProfileNotFoundException()
            else:
                raise error


class ChatConversationCreateAPIView(GenericAPIView):
    renderer_classes = (StandardRenderer,)
    serializer_class = MessageSerializer
    permission_classes = (permissions.IsAuthenticated, HasProfile)

    """
        @param oid: Other User Id
    """

    # FIXME: check if chat already exists! Not implemented yet
    def post(self, request, oid):
        user = request.user
        if user.pk == int(oid):
            raise exceptions.ChattingSelfNotPermitted()
        try:
            other_user = User.objects.get(pk=oid)
        except User.DoesNotExist:
            raise exceptions.NoChatUserWithId()
        serializer = self.serializer_class(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as exception:
            raise validation_exceptions(exception)
        chat = user.chats.create(type='CONVERSATION')
        chat.users.add(other_user)
        serializer.save(user=user, chat=chat)
        chat_serializer = ChatSerializer(instance=chat)
        chat_serializer.uid = user.pk
        return Response(chat_serializer.data, status=status.HTTP_200_OK)

    def permission_denied(self, request, message=None, code=None):
        try:
            super(ChatConversationCreateAPIView, self).permission_denied(request, message, code)
        except NotAuthenticated:
            raise NotAuthenticatedRequest
        except Exception as error:
            if code == HasProfile.code:
                raise AuthProfileNotFoundException()
            else:
                raise error
