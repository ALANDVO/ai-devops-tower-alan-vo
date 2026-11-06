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


# Streaming tests

class MockStreamResponse:
    """Mock streaming response for testing."""
    def __init__(self, lines, status_code=200):
        self._lines = lines
        self.status_code = status_code
        self.text = "\n".join(lines)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def aiter_lines(self):
        for line in self._lines:
            yield line

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx
            raise httpx.HTTPStatusError("Error", request=MagicMock(), response=self)


@pytest.mark.asyncio
async def test_openai_adapter_stream_success():
    """Test OpenAI-compatible adapter streams response correctly."""
    from app.services.llm import LLMStreamChunk

    adapter = OpenAICompatibleAdapter(api_key="test-key", model="gpt-4", base_url="https://api.openai.com/v1")

    stream_lines = [
        'data: {"choices": [{"delta": {"content": "Hello"}, "finish_reason": null}]}',
        'data: {"choices": [{"delta": {"content": " world"}, "finish_reason": null}]}',
        'data: {"choices": [{"delta": {}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15}}',
        'data: [DONE]',
    ]

    with patch("httpx.AsyncClient.stream") as mock_stream:
        mock_stream.return_value = MockStreamResponse(stream_lines)
        chunks = []
        async for chunk in adapter.stream("Test prompt"):
            chunks.append(chunk)

    assert len(chunks) == 3
    assert chunks[0].content == "Hello"
    assert chunks[0].is_final is False
    assert chunks[1].content == " world"
    assert chunks[1].is_final is False
    assert chunks[2].content == ""
    assert chunks[2].is_final is True
    assert chunks[2].usage == {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15}
    assert all(c.error is None for c in chunks)


@pytest.mark.asyncio
async def test_anthropic_adapter_stream_success():
    """Test Anthropic adapter streams response correctly."""
    from app.services.llm import LLMStreamChunk

    adapter = AnthropicAdapter(api_key="test-key", model="claude-3", base_url="https://api.anthropic.com/v1")

    stream_lines = [
        'data: {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Hello"}}',
        'data: {"type": "content_block_delta", "delta": {"type": "text_delta", "text": " world"}}',
        'data: {"type": "message_stop", "message": {"usage": {"input_tokens": 5, "output_tokens": 10}}}',
    ]

    with patch("httpx.AsyncClient.stream") as mock_stream:
        mock_stream.return_value = MockStreamResponse(stream_lines)
        chunks = []
        async for chunk in adapter.stream("Test prompt"):
            chunks.append(chunk)

    assert len(chunks) == 3
    assert chunks[0].content == "Hello"
    assert chunks[0].is_final is False
    assert chunks[1].content == " world"
    assert chunks[1].is_final is False
    assert chunks[2].content == ""
    assert chunks[2].is_final is True
    assert chunks[2].usage == {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15}
    assert all(c.error is None for c in chunks)


@pytest.mark.asyncio
async def test_gemini_adapter_stream_success():
    """Test Gemini adapter streams response correctly."""
    from app.services.llm import LLMStreamChunk

    adapter = GeminiAdapter(api_key="test-key", model="gemini-pro", base_url="https://generativelanguage.googleapis.com/v1beta")

    stream_lines = [
        '{"candidates": [{"content": {"parts": [{"text": "Hello world"}]}, "finishReason": "STOP"}], "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 10, "totalTokenCount": 15}}',
    ]

    with patch("httpx.AsyncClient.stream") as mock_stream:
        mock_stream.return_value = MockStreamResponse(stream_lines)
        chunks = []
        async for chunk in adapter.stream("Test prompt"):
            chunks.append(chunk)

    assert len(chunks) == 2
    assert chunks[0].content == "Hello world"
    assert chunks[0].is_final is True
    assert chunks[0].usage is None  # usage comes in final chunk
    assert chunks[1].content == ""
    assert chunks[1].is_final is True
    assert chunks[1].usage == {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15}
    assert all(c.error is None for c in chunks)


@pytest.mark.asyncio
async def test_ollama_adapter_stream_success():
    """Test Ollama adapter streams response correctly."""
    from app.services.llm import LLMStreamChunk

    adapter = OllamaAdapter(api_key="", model="llama3", base_url="http://localhost:11434")

    stream_lines = [
        '{"message": {"content": "Hello"}, "done": false}',
        '{"message": {"content": " world"}, "done": false}',
        '{"message": {"content": ""}, "done": true, "prompt_eval_count": 5, "eval_count": 10}',
    ]

    with patch("httpx.AsyncClient.stream") as mock_stream:
        mock_stream.return_value = MockStreamResponse(stream_lines)
        chunks = []
        async for chunk in adapter.stream("Test prompt"):
            chunks.append(chunk)

    assert len(chunks) == 3
    assert chunks[0].content == "Hello"
    assert chunks[0].is_final is False
    assert chunks[1].content == " world"
    assert chunks[1].is_final is False
    assert chunks[2].content == ""
    assert chunks[2].is_final is True
    assert chunks[2].usage == {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15}
    assert all(c.error is None for c in chunks)


@pytest.mark.asyncio
async def test_openai_adapter_stream_http_error():
    """Test OpenAI adapter handles streaming HTTP errors."""
    from app.services.llm import LLMStreamChunk

    adapter = OpenAICompatibleAdapter(api_key="test-key", model="gpt-4", base_url="https://api.openai.com/v1")

    with patch("httpx.AsyncClient.stream") as mock_stream:
        mock_stream.return_value = MockStreamResponse([], status_code=401)
        chunks = []
        async for chunk in adapter.stream("Test prompt"):
            chunks.append(chunk)

    assert len(chunks) == 1
    assert chunks[0].content == ""
    assert chunks[0].is_final is True
    assert "401" in chunks[0].error


@pytest.mark.asyncio
async def test_stream_llm_convenience_function():
    """Test stream_llm convenience function."""
    from app.services.llm import stream_llm, LLMStreamChunk

    stream_lines = [
        'data: {"choices": [{"delta": {"content": "Hello"}, "finish_reason": null}]}',
        'data: {"choices": [{"delta": {"content": " world"}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15}}',
    ]

    with patch("app.services.llm.get_llm_adapter") as mock_get_adapter:
        mock_adapter = AsyncMock()
        async def mock_stream(prompt, system_prompt=None):
            for line in stream_lines:
                if line.startswith("data: "):
                    data_str = line[6:]
                    import json
                    data = json.loads(data_str)
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    finish_reason = data.get("choices", [{}])[0].get("finish_reason")
                    if content:
                        yield LLMStreamChunk(content=content, is_final=finish_reason is not None)
                    if finish_reason:
                        usage = data.get("usage")
                        yield LLMStreamChunk(content="", is_final=True, usage=usage)
                        break
        mock_adapter.stream = mock_stream
        mock_get_adapter.return_value = mock_adapter

        chunks = []
        async for chunk in stream_llm("Test prompt"):
            chunks.append(chunk)

    assert len(chunks) == 3
    assert chunks[0].content == "Hello"
    assert chunks[0].is_final is False
    assert chunks[1].content == " world"
    assert chunks[1].is_final is True
    assert chunks[2].content == ""
    assert chunks[2].is_final is True
    assert chunks[2].usage == {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15}