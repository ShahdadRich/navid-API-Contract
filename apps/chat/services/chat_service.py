from ..models import Message, Conversation
from .llm_service import LLMService

class ChatService:
    def __init__(self):
        self.llm_service = LLMService()

    def create_user_message(self, conversation, content):
        message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content=content
        )
        # Update conversation timestamp
        conversation.save()  # Triggers auto_now=True for updated_at
        return message

    def get_ai_response(self, conversation, user_content):
        # 1. Prepare history (optional, for now just the current message)
        # 2. Call LLM
        ai_content = self.llm_service.get_response([{"role": "user", "content": user_content}])

        # 3. Save AI message
        ai_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content=ai_content
        )

        # 4. Update conversation timestamp
        conversation.save()

        # 5. Trigger Auto-Titling if it's the first exchange
        if conversation.messages.count() == 2:
            from ..tasks import generate_title_task
            generate_title_task.delay(str(conversation.id))

        return ai_message

    def stream_ai_response(self, conversation, user_content):
        # 1. Prepare history (optional)
        # 2. Call LLM streaming
        generator = self.llm_service.get_streaming_response([{"role": "user", "content": user_content}])

        full_content = ""
        for chunk in generator:
            full_content += chunk
            yield chunk

        # 3. After streaming finishes, save AI message
        ai_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content=full_content
        )

        # 4. Update conversation timestamp
        conversation.save()

        # 5. Trigger Auto-Titling if it's the first exchange
        if conversation.messages.count() == 2:
            from ..tasks import generate_title_task
            generate_title_task.delay(str(conversation.id))

        yield f"__ID__:{ai_message.id}"
