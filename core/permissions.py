from rest_framework.permissions import BasePermission


class HasProfile(BasePermission):
    code = 'no_profile'

    def has_permission(self, request, view):
        return request.user.has_profile()
