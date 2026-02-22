from celery import shared_task
from .models import Conversation
from .services.llm_service import LLMService

@shared_task
def generate_title_task(conversation_id):
    try:
        conversation = Conversation.objects.get(id=conversation_id)
        # Get the first user message
        first_message = conversation.messages.filter(role="user").first()
        if not first_message:
            return

        llm_service = LLMService()
        prompt = f"Summarize the following user request in 3-5 words to be used as a chat title: {first_message.content}"

        title = llm_service.get_response([{"role": "user", "content": prompt}])

        # Clean up title (remove quotes if any)
        title = title.strip().strip('"').strip("'")

        conversation.title = title
        conversation.save()
    except Conversation.DoesNotExist:
        pass
