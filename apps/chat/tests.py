import pytest
from unittest.mock import patch
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.authentication.models import User
from apps.chat.models import Conversation, Message

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="test@example.com",
        password="password123",
        full_name="Test User"
    )

@pytest.mark.django_db
class TestConversationEndpoints:
    def test_list_conversations_unauthenticated(self, api_client):
        url = reverse("conversation-list")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_conversations_authenticated(self, api_client, user):
        api_client.force_authenticate(user=user)
        url = reverse("conversation-list")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data

    def test_create_conversation(self, api_client, user):
        api_client.force_authenticate(user=user)
        url = reverse("conversation-list")
        response = api_client.get(url)
        initial_count = response.data["count"]

        response = api_client.post(url, {})
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["title"] == "New Chat"

        response = api_client.get(url)
        assert response.data["count"] == initial_count + 1

    def test_update_conversation_title(self, api_client, user):
        api_client.force_authenticate(user=user)
        conv = Conversation.objects.create(user=user, title="Old Title")
        url = reverse("conversation-detail", args=[conv.id])

        response = api_client.patch(url, {"title": "New Title"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == "New Title"

        conv.refresh_from_db()
        assert conv.title == "New Title"

    def test_delete_conversation(self, api_client, user):
        api_client.force_authenticate(user=user)
        conv = Conversation.objects.create(user=user)
        url = reverse("conversation-detail", args=[conv.id])

        response = api_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Conversation.objects.filter(id=conv.id).count() == 0

    def test_access_other_user_conversation(self, api_client, user):
        other_user = User.objects.create_user(
            email="other@example.com",
            password="password123",
            full_name="Other User"
        )
        conv = Conversation.objects.create(user=other_user)

        api_client.force_authenticate(user=user)
        url = reverse("conversation-detail", args=[conv.id])

        response = api_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_messages_pagination(self, api_client, user):
        api_client.force_authenticate(user=user)
        conv = Conversation.objects.create(user=user)
        # Create 60 messages (more than default page size of 50)
        for i in range(60):
            Message.objects.create(
                conversation=conv,
                role=Message.Role.USER,
                content=f"Message {i}"
            )

        url = reverse("conversation-messages", args=[conv.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 50
        assert response.data["nextCursor"] is not None

    def test_create_message_flow(self, api_client, user):
        api_client.force_authenticate(user=user)
        conv = Conversation.objects.create(user=user)
        url = reverse("conversation-messages", args=[conv.id])

        response = api_client.post(url, {"content": "Hello AI"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["role"] == "assistant"

        # Verify messages in DB
        assert Message.objects.filter(conversation=conv).count() == 2

    def test_mandatory_feedback_logic(self, api_client, user):
        api_client.force_authenticate(user=user)
        conv = Conversation.objects.create(user=user)
        url = reverse("conversation-messages", args=[conv.id])

        # 1. Send first message
        api_client.post(url, {"content": "Hello AI"})

        # 2. Try to send second message immediately (should be blocked)
        response = api_client.post(url, {"content": "Another message"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "You must rate the previous AI response" in str(response.data)

        # 3. Provide feedback
        ai_message = Message.objects.filter(conversation=conv, role="assistant").last()
        feedback_url = reverse("message-feedback", args=[ai_message.id])
        response = api_client.patch(feedback_url, {"feedback": "good"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["feedback"] == "good"

        # 4. Send second message again (should succeed)
        response = api_client.post(url, {"content": "Another message"})
        assert response.status_code == status.HTTP_200_OK

    def test_context_management(self, api_client, user):
        api_client.force_authenticate(user=user)
        conv = Conversation.objects.create(user=user)

        # Create some history
        Message.objects.create(conversation=conv, role="user", content="msg1")
        Message.objects.create(conversation=conv, role="assistant", content="reply1", feedback="good")
        Message.objects.create(conversation=conv, role="user", content="msg2")
        Message.objects.create(conversation=conv, role="assistant", content="reply2", feedback="bad")

        url = reverse("conversation-messages", args=[conv.id])

        with patch("apps.chat.services.llm_service.LLMService.get_response") as mock_get_response:
            mock_get_response.return_value = "AI Response"

            api_client.post(url, {"content": "new message"})

            # Check that context was passed
            args, kwargs = mock_get_response.call_args
            context = args[0]

            # Should have 4 historical messages + 1 new user message = 5
            assert len(context) == 5
            assert context[0]["content"] == "msg1"
            assert context[1]["content"] == "reply1"
            assert context[2]["content"] == "msg2"
            assert context[3]["content"] == "reply2"
            assert context[4]["content"] == "new message"

    def test_context_management_streaming(self, api_client, user):
        api_client.force_authenticate(user=user)
        conv = Conversation.objects.create(user=user)

        # Create some history
        Message.objects.create(conversation=conv, role="user", content="msg1")
        Message.objects.create(conversation=conv, role="assistant", content="reply1", feedback="good")

        url = reverse("conversation-stream-message", args=[conv.id])

        with patch("apps.chat.services.llm_service.LLMService.get_streaming_response") as mock_get_stream:
            mock_get_stream.return_value = iter(["chunk1", "chunk2"])

            response = api_client.post(url, {"content": "new stream"})
            # consume generator to trigger logic
            b"".join(response.streaming_content)

            # Check that context was passed
            args, kwargs = mock_get_stream.call_args
            context = args[0]

            assert len(context) == 3
            assert context[0]["content"] == "msg1"
            assert context[1]["content"] == "reply1"
            assert context[2]["content"] == "new stream"

    def test_feedback_only_for_assistant(self, api_client, user):
        api_client.force_authenticate(user=user)
        conv = Conversation.objects.create(user=user)
        user_msg = Message.objects.create(conversation=conv, role="user", content="Hi")

        feedback_url = reverse("message-feedback", args=[user_msg.id])
        response = api_client.patch(feedback_url, {"feedback": "good"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Only assistant messages can be rated." in str(response.data)

    def test_auto_titling(self, api_client, user):
        api_client.force_authenticate(user=user)
        conv = Conversation.objects.create(user=user, title="New Chat")
        url = reverse("conversation-messages", args=[conv.id])

        # First message exchange
        api_client.post(url, {"content": "Explain quantum physics"})

        conv.refresh_from_db()
        # Mock LLM returns "This is a mock response from the AI." for any request.
        # But for titling it's also called.
        assert conv.title != "New Chat"
        assert conv.title == "This is a mock response from the AI."
        assert Message.objects.filter(conversation=conv, role="user").count() == 1
        assert Message.objects.filter(conversation=conv, role="assistant").count() == 1

    def test_stream_message_flow(self, api_client, user):
        api_client.force_authenticate(user=user)
        conv = Conversation.objects.create(user=user)
        url = reverse("conversation-stream-message", args=[conv.id])

        response = api_client.post(url, {"content": "Stream me"})
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "text/event-stream"

        # Collect streaming content
        content = b"".join(response.streaming_content).decode()
        assert '{"chunk":' in content
        assert '"status": "done"' in content

        # Verify messages in DB
        assert Message.objects.filter(conversation=conv).count() == 2
