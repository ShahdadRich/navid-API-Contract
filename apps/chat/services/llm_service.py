import time
import abc

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

class LLMService:
    def __init__(self):
        # In a real app, this would be determined by settings
        self.provider = MockLLMService()

    def get_response(self, messages):
        return self.provider.get_response(messages)

    def get_streaming_response(self, messages):
        return self.provider.get_streaming_response(messages)
