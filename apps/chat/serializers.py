from rest_framework import serializers
from .models import Conversation, Message

class ConversationSerializer(serializers.ModelSerializer):
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = Conversation
        fields = ["id", "title", "createdAt", "updatedAt"]
        read_only_fields = ["id", "createdAt", "updatedAt"]

class MessageSerializer(serializers.ModelSerializer):
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = Message
        fields = ["id", "role", "content", "createdAt"]
        read_only_fields = ["id", "createdAt"]

class MessageCreateSerializer(serializers.Serializer):
    content = serializers.CharField(required=True)
