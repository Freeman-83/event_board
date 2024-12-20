from rest_framework import permissions


class IsAdminAuthorOrReadOnly(permissions.BasePermission):
    """Пермишн, дающий права только автору."""
    def has_permission(self, request, view):
        return (request.method in permissions.SAFE_METHODS
                or request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return (request.method in permissions.SAFE_METHODS
                or request.user.is_authenticated
                and (request.user.is_staff
                     or obj == request.user))
