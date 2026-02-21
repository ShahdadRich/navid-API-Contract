from rest_framework import permissions

class IsConversationOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of a conversation to access it.
    """
    def has_object_permission(self, request, view, obj):
        # The obj here is expected to be a Conversation instance
        return obj.user == request.user
