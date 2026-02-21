import json
from django.http import StreamingHttpResponse
from rest_framework import viewsets, status, response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer, MessageCreateSerializer
from .permissions import IsConversationOwner
from .pagination import ConversationPagination, MessageCursorPagination
from .services.chat_service import ChatService

class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated, IsConversationOwner]
    pagination_class = ConversationPagination

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["get", "post"], url_path="messages")
    def messages(self, request, pk=None):
        conversation = self.get_object()

        if request.method == "GET":
            messages = conversation.messages.all()
            paginator = MessageCursorPagination()
            page = paginator.paginate_queryset(messages, request)
            if page is not None:
                serializer = MessageSerializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)

            serializer = MessageSerializer(messages, many=True)
            return response.Response(serializer.data)

        elif request.method == "POST":
            serializer = MessageCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            content = serializer.validated_data["content"]
            chat_service = ChatService()

            # 1. Save user message
            chat_service.create_user_message(conversation, content)

            # 2. Get AI response
            ai_message = chat_service.get_ai_response(conversation, content)

            return response.Response(
                MessageSerializer(ai_message).data,
                status=status.HTTP_200_OK
            )

    @action(detail=True, methods=["post"], url_path="messages/stream")
    def stream_message(self, request, pk=None):
        conversation = self.get_object()
        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        content = serializer.validated_data["content"]
        chat_service = ChatService()

        # 1. Save user message
        chat_service.create_user_message(conversation, content)

        # 2. Return StreamingHttpResponse
        def event_stream():
            for chunk in chat_service.stream_ai_response(conversation, content):
                if chunk.startswith("__ID__:"):
                    message_id = chunk.replace("__ID__:", "")
                    yield f'data: {{"status": "done", "fullMessageId": "{message_id}"}}\n\n'
                else:
                    yield f'data: {json.dumps({"chunk": chunk})}\n\n'

        return StreamingHttpResponse(event_stream(), content_type="text/event-stream")
