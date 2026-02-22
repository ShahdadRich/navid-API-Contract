import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from apps.chat.services.llm_service import LLMService

def test_llm_connectivity():
    print(f"Testing LLM Provider: {settings.LLM_PROVIDER}")
    print(f"Base URL: {settings.LLM_BASE_URL}")
    print(f"Model: {settings.LLM_MODEL}")
    llm = LLMService()

    messages = [{"role": "user", "content": "Say hello!"}]

    print("\n--- Testing Standard Response ---")
    try:
        response = llm.get_response(messages)
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n--- Testing Streaming Response ---")
    try:
        print("Streaming: ", end="", flush=True)
        for chunk in llm.get_streaming_response(messages):
            print(chunk, end="", flush=True)
        print("\nDone.")
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    test_llm_connectivity()
