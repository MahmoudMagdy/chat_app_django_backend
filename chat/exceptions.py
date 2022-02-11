from core.exceptions import FlamesCLoudException
from rest_framework import status

"""
    Rest Framework Exceptions
"""


class ChatException(FlamesCLoudException):
    status_code = status.HTTP_400_BAD_REQUEST


class NoChatWithId(ChatException):
    code = 'no_chat_with_id'
    message = 'No chat with provided id.'


class ChattingSelfNotPermitted(ChatException):
    code = 'chatting_self_not_permitted'
    message = 'Chatting self not permitted.'


class NoChatUserWithId(ChatException):
    code = 'no_chat_user_with_id'
    message = 'No chat with provided id.'


class NoChatMatched(ChatException):
    code = 'no_chat_matched'
    message = 'No chat matched.'


class NotChatMember(ChatException):
    status_code = status.HTTP_403_FORBIDDEN
    code = 'not_chat_member'
    message = 'User is not chat member.'


class NoChatRequested(ChatException):
    code = 'no_chat_requested'
    message = 'No chat requested.'


"""
    Websocket Exceptions Codes
"""


def auth_user_not_found():
    return 4003


def unauthoraized_chat_access():
    return 4004


def chat_not_found():
    return 3003


def chat_message_invalid():
    return 3001
