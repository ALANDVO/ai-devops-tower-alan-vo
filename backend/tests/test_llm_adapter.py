"""Tests for multi-provider LLM adapter."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.llm import (
    OpenAICompatibleAdapter,
    AnthropicAdapter,
    GeminiAdapter,
    OllamaAdapter,
    get_llm_adapter,
    LLMResponse,
)


class MockResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code
        self.text = str(json_data)

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx
            raise httpx.HTTPStatusError("Error", request=MagicMock(), response=self)


@pytest.mark.asyncio
async def test_openai_adapter_success():
    """Test OpenAI-compatible adapter returns normalized response."""
    adapter = OpenAICompatibleAdapter(api_key="test-key", model="gpt-4", base_url="https://api.openai.com/v1")

    mock_response = MockResponse({
        "choices": [{"message": {"content": "Test response"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    })

    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_response)):
        result = await adapter.complete("Test prompt")

    assert isinstance(result, LLMResponse)
    assert result.content == "Test response"
    assert result.provider == "openai-compatible"
    assert result.model == "gpt-4"
    assert result.usage == {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    assert result.error is None


@pytest.mark.asyncio
async def test_openai_adapter_http_error():
    """Test OpenAI adapter handles HTTP errors gracefully."""
    adapter = OpenAICompatibleAdapter(api_key="test-key", model="gpt-4")

    mock_response = MockResponse({"error": "Invalid API key"}, status_code=401)

    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_response)):
        result = await adapter.complete("Test prompt")

    assert result.content == ""
    assert result.provider == "openai-compatible"
    assert result.error is not None
    assert "401" in result.error


@pytest.mark.asyncio
async def test_anthropic_adapter_success():
    """Test Anthropic adapter returns normalized response."""
    adapter = AnthropicAdapter(api_key="test-key", model="claude-3")

    mock_response = MockResponse({
        "content": [{"text": "Anthropic response"}],
        "usage": {"input_tokens": 15, "output_tokens": 25}
    })

    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_response)):
        result = await adapter.complete("Test prompt", system_prompt="System")

    assert result.content == "Anthropic response"
    assert result.provider == "anthropic"
    assert result.model == "claude-3"
    assert result.usage is not None


@pytest.mark.asyncio
async def test_anthropic_adapter_error():
    """Test Anthropic adapter handles errors."""
    adapter = AnthropicAdapter(api_key="test-key", model="claude-3")

    mock_response = MockResponse({"error": "Rate limit"}, status_code=429)

    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_response)):
        result = await adapter.complete("Test prompt")

    assert result.error is not None
    assert "429" in result.error


@pytest.mark.asyncio
async def test_gemini_adapter_success():
    """Test Gemini adapter returns normalized response."""
    adapter = GeminiAdapter(api_key="test-key", model="gemini-pro")

    mock_response = MockResponse({
        "candidates": [{
            "content": {"parts": [{"text": "Gemini response"}]}
        }],
        "usageMetadata": {
            "promptTokenCount": 10,
            "candidatesTokenCount": 20,
            "totalTokenCount": 30
        }
    })

    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_response)):
        result = await adapter.complete("Test prompt")

    assert result.content == "Gemini response"
    assert result.provider == "gemini"
    assert result.model == "gemini-pro"
    assert result.usage == {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}


@pytest.mark.asyncio
async def test_gemini_adapter_no_candidates():
    """Test Gemini adapter handles empty candidates."""
    adapter = GeminiAdapter(api_key="test-key", model="gemini-pro")

    mock_response = MockResponse({"candidates": []})

    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_response)):
        result = await adapter.complete("Test prompt")

    assert result.error is not None
    assert "No candidates" in result.error


@pytest.mark.asyncio
async def test_ollama_adapter_success():
    """Test Ollama adapter returns normalized response."""
    adapter = OllamaAdapter(model="llama3", base_url="http://localhost:11434")

    mock_response = MockResponse({
        "message": {"content": "Ollama response"},
        "prompt_eval_count": 100,
        "eval_count": 50
    })

    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_response)):
        result = await adapter.complete("Test prompt")

    assert result.content == "Ollama response"
    assert result.provider == "ollama"
    assert result.model == "llama3"
    assert result.usage["prompt_tokens"] == 100
    assert result.usage["completion_tokens"] == 50


@pytest.mark.asyncio
async def test_ollama_adapter_with_api_key():
    """Test Ollama adapter includes Authorization header when API key provided."""
    adapter = OllamaAdapter(api_key="ollama-key", model="llama3", base_url="http://localhost:11434")

    mock_response = MockResponse({"message": {"content": "Response"}})

    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_response)) as mock_post:
        await adapter.complete("Test prompt")

    # Check that Authorization header was included
    call_args = mock_post.call_args
    headers = call_args.kwargs.get("headers", {})
    assert headers.get("Authorization") == "Bearer ollama-key"


@pytest.mark.asyncio
async def test_get_llm_adapter_openai():
    """Test factory returns OpenAI adapter for openai provider."""
    from app.core.config import settings
    settings.LLM_PROVIDER = "openai"
    settings.LLM_API_KEY = "test-key"
    settings.LLM_MODEL = "gpt-4"
    settings.LLM_BASE_URL = ""
    settings.LLM_MAX_TOKENS = 4096

    adapter = get_llm_adapter()
    assert isinstance(adapter, OpenAICompatibleAdapter)


@pytest.mark.asyncio
async def test_get_llm_adapter_anthropic():
    """Test factory returns Anthropic adapter for anthropic provider."""
    from app.core.config import settings
    settings.LLM_PROVIDER = "anthropic"
    settings.LLM_API_KEY = "test-key"
    settings.LLM_MODEL = "claude-3"
    settings.LLM_BASE_URL = ""
    settings.LLM_MAX_TOKENS = 4096

    adapter = get_llm_adapter()
    assert isinstance(adapter, AnthropicAdapter)


@pytest.mark.asyncio
async def test_get_llm_adapter_gemini():
    """Test factory returns Gemini adapter for gemini provider."""
    from app.core.config import settings
    settings.LLM_PROVIDER = "gemini"
    settings.LLM_API_KEY = "test-key"
    settings.LLM_MODEL = "gemini-pro"
    settings.LLM_BASE_URL = ""
    settings.LLM_MAX_TOKENS = 4096

    adapter = get_llm_adapter()
    assert isinstance(adapter, GeminiAdapter)


@pytest.mark.asyncio
async def test_get_llm_adapter_ollama():
    """Test factory returns Ollama adapter for ollama provider."""
    from app.core.config import settings
    settings.LLM_PROVIDER = "ollama"
    settings.LLM_API_KEY = ""
    settings.LLM_MODEL = "llama3"
    settings.LLM_BASE_URL = "http://localhost:11434"
    settings.LLM_MAX_TOKENS = 4096

    adapter = get_llm_adapter()
    assert isinstance(adapter, OllamaAdapter)


@pytest.mark.asyncio
async def test_get_llm_adapter_unknown_defaults_to_openai():
    """Test factory defaults to OpenAI-compatible for unknown provider."""
    from app.core.config import settings
    settings.LLM_PROVIDER = "unknown-provider"
    settings.LLM_API_KEY = "test-key"
    settings.LLM_MODEL = "test-model"
    settings.LLM_BASE_URL = ""
    settings.LLM_MAX_TOKENS = 4096

    adapter = get_llm_adapter()
    assert isinstance(adapter, OpenAICompatibleAdapter)


@pytest.mark.asyncio
async def test_redact_key():
    """Test API key redaction helper."""
    adapter = OpenAICompatibleAdapter(api_key="sk-1234567890abcdef", model="gpt-4")
    assert adapter._redact_key("sk-1234567890abcdef") == "sk-1***********cdef"
    assert adapter._redact_key("short") == "<redacted>"
    assert adapter._redact_key("") == "<empty>"