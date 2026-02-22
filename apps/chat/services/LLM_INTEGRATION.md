# LLM Integration Guide

This project uses a modular provider system for Large Language Model (LLM) integration, located in `apps/chat/services/llm_service.py`.

## Supported Providers

### 1. Mock Provider (`mock`)
- **Use Case**: Default for development and testing. Does not require an API key or internet connection.
- **Behavior**: Returns a static string and simulates a typing effect for streaming.

### 2. OpenAI Provider (`openai`)
- **Use Case**: Production or development using OpenAI models (GPT-4o, etc.).
- **Configuration**:
  ```bash
  LLM_PROVIDER=openai
  LLM_API_KEY=your_openai_api_key
  LLM_MODEL=gpt-4o
  ```

### 3. Local LLM (via OpenAI Compatibility)
Most local LLM runners provide an OpenAI-compatible API. You can use the `openai` provider type but redirect the `BASE_URL`.

#### Example: Ollama
1. Install [Ollama](https://ollama.com/).
2. Run a model: `ollama run llama3`.
3. Configure the backend:
   ```bash
   LLM_PROVIDER=openai
   LLM_API_KEY=ollama  # Ollama doesn't require a real key for local use
   LLM_BASE_URL=http://localhost:11434/v1
   LLM_MODEL=llama3
   ```

#### Example: LM Studio
1. Open LM Studio and start the "Local Server".
2. Configure the backend:
   ```bash
   LLM_PROVIDER=openai
   LLM_API_KEY=lm-studio
   LLM_BASE_URL=http://localhost:1234/v1
   LLM_MODEL=model-identifier-here
   ```

## Adding a New Provider

To add a provider that is *not* OpenAI-compatible:

1.  **Define the Service**: In `apps/chat/services/llm_service.py`, create a new class inheriting from `BaseLLMService`.
    ```python
    class MyNewProviderService(BaseLLMService):
        def get_response(self, messages):
            # Your implementation here
            pass
        def get_streaming_response(self, messages):
            # Your implementation here (generator)
            pass
    ```
2.  **Register the Provider**: Update the `LLMService` factory class:
    ```python
    class LLMService:
        def __init__(self):
            provider_type = getattr(settings, "LLM_PROVIDER", "mock")
            if provider_type == "openai":
                self.provider = OpenAIService()
            elif provider_type == "my-new-provider":
                self.provider = MyNewProviderService()
            else:
                self.provider = MockLLMService()
    ```

## Settings Summary

| Environment Variable | Description | Default |
| :--- | :--- | :--- |
| `LLM_PROVIDER` | `mock`, `openai`, or `local` | `mock` |
| `LLM_API_KEY` | API Key for the provider | `sk-mock-key` |
| `LLM_BASE_URL` | API Endpoint (change this for local LLMs) | `https://api.openai.com/v1` |
| `LLM_MODEL` | Model name (e.g., `gpt-4o`, `llama3`) | `gpt-4o` |
