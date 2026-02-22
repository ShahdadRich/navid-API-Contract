import time
import abc
import os
from django.conf import settings
from openai import OpenAI

class BaseLLMService(abc.ABC):
    @abc.abstractmethod
    def get_response(self, messages):
        pass

    @abc.abstractmethod
    def get_streaming_response(self, messages):
        pass

class MockLLMService(BaseLLMService):
    def get_response(self, messages):
        # Simulate network delay
        time.sleep(1)
        return "This is a mock response from the AI."

    def get_streaming_response(self, messages):
        response_text = "This is a streaming mock response from the AI."
        for word in response_text.split():
            yield word + " "
            time.sleep(0.1)

class OpenAIService(BaseLLMService):
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL
        )
        self.model = settings.LLM_MODEL

    def get_response(self, messages):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=False
        )
        return response.choices[0].message.content

    def get_streaming_response(self, messages):
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True
        )
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content

class LLMService:
    def __init__(self):
        provider_type = getattr(settings, "LLM_PROVIDER", "mock")
        if provider_type == "openai":
            self.provider = OpenAIService()
        else:
            self.provider = MockLLMService()

    def get_response(self, messages):
        return self.provider.get_response(messages)

    def get_streaming_response(self, messages):
        return self.provider.get_streaming_response(messages)
