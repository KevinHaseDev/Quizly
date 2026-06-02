from rest_framework.permissions import BasePermission


class IsQuizOwner(BasePermission):
    """Allow access only to quiz owners."""

    message = 'You do not have permission to access this quiz.'

    def has_object_permission(self, request, view, obj):
        """Check if the user is the owner of the quiz."""
        return obj.owner_id == request.user.id
