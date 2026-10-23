"""Shared LLM adapter supporting multiple providers."""

import json
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass

import httpx

from app.core.config import settings


@dataclass
class LLMResponse:
    """Normalized LLM response."""
    content: str
    provider: str
    model: str
    usage: Optional[Dict[str, int]] = None
    error: Optional[str] = None


class LLMAdapter(ABC):
    """Abstract base for LLM provider adapters."""

    def __init__(self, api_key: str, model: str, base_url: str = "", max_tokens: int = 4096, timeout: float = 60.0):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.max_tokens = max_tokens
        self.timeout = timeout

    @abstractmethod
    async def complete(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """Send completion request and return normalized response."""
        pass

    def _redact_key(self, key: str) -> str:
        """Redact API key for logging."""
        if not key:
            return "<empty>"
        if len(key) <= 8:
            return "<redacted>"
        return f"{key[:4]}{'*' * (len(key) - 8)}{key[-4:]}"


class OpenAICompatibleAdapter(LLMAdapter):
    """Adapter for OpenAI-compatible APIs (OpenAI, LiteLLM, OpenRouter, Ollama)."""

    def __init__(self, api_key: str, model: str, base_url: str = "", max_tokens: int = 4096, timeout: float = 60.0):
        super().__init__(api_key, model, base_url, max_tokens, timeout)
        self.endpoint = (base_url or "https://api.openai.com/v1").rstrip("/") + "/chat/completions"

    async def complete(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    self.endpoint,
                    headers=headers,
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": self.max_tokens,
                        "temperature": 0.2,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                return LLMResponse(
                    content=data["choices"][0]["message"]["content"],
                    provider="openai-compatible",
                    model=self.model,
                    usage=data.get("usage"),
                )
        except httpx.HTTPStatusError as e:
            return LLMResponse(
                content="",
                provider="openai-compatible",
                model=self.model,
                error=f"HTTP {e.response.status_code}: {e.response.text[:500]}",
            )
        except Exception as e:
            return LLMResponse(
                content="",
                provider="openai-compatible",
                model=self.model,
                error=str(e),
            )


class AnthropicAdapter(LLMAdapter):
    """Adapter for Anthropic Messages API."""

    def __init__(self, api_key: str, model: str, base_url: str = "", max_tokens: int = 4096, timeout: float = 60.0):
        super().__init__(api_key, model, base_url, max_tokens, timeout)
        self.endpoint = (base_url or "https://api.anthropic.com/v1").rstrip("/") + "/messages"

    async def complete(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        messages = [{"role": "user", "content": prompt}]

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": 0.2,
        }
        if system_prompt:
            payload["system"] = system_prompt

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    self.endpoint,
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()

                return LLMResponse(
                    content=data["content"][0]["text"],
                    provider="anthropic",
                    model=self.model,
                    usage=data.get("usage"),
                )
        except httpx.HTTPStatusError as e:
            return LLMResponse(
                content="",
                provider="anthropic",
                model=self.model,
                error=f"HTTP {e.response.status_code}: {e.response.text[:500]}",
            )
        except Exception as e:
            return LLMResponse(
                content="",
                provider="anthropic",
                model=self.model,
                error=str(e),
            )


class GeminiAdapter(LLMAdapter):
    """Adapter for Google Gemini generateContent API."""

    def __init__(self, api_key: str, model: str, base_url: str = "", max_tokens: int = 4096, timeout: float = 60.0):
        super().__init__(api_key, model, base_url, max_tokens, timeout)
        self.endpoint = (
            (base_url or "https://generativelanguage.googleapis.com/v1beta")
            .rstrip("/")
            + f"/models/{self.model}:generateContent?key={self.api_key}"
        )

    async def complete(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": system_prompt}]})
            contents.append({"role": "model", "parts": [{"text": "Understood."}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": self.max_tokens,
                "temperature": 0.2,
            },
        }

        headers = {"Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    self.endpoint,
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()

                # Extract text from Gemini response
                candidates = data.get("candidates", [])
                if not candidates:
                    return LLMResponse(
                        content="",
                        provider="gemini",
                        model=self.model,
                        error="No candidates in response",
                    )
                parts = candidates[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts)

                usage = data.get("usageMetadata")
                usage_dict = None
                if usage:
                    usage_dict = {
                        "prompt_tokens": usage.get("promptTokenCount", 0),
                        "completion_tokens": usage.get("candidatesTokenCount", 0),
                        "total_tokens": usage.get("totalTokenCount", 0),
                    }

                return LLMResponse(
                    content=text,
                    provider="gemini",
                    model=self.model,
                    usage=usage_dict,
                )
        except httpx.HTTPStatusError as e:
            return LLMResponse(
                content="",
                provider="gemini",
                model=self.model,
                error=f"HTTP {e.response.status_code}: {e.response.text[:500]}",
            )
        except Exception as e:
            return LLMResponse(
                content="",
                provider="gemini",
                model=self.model,
                error=str(e),
            )


class OllamaAdapter(LLMAdapter):
    """Adapter for Ollama local API (OpenAI-compatible with defaults)."""

    def __init__(self, api_key: str = "", model: str = "llama3", base_url: str = "http://localhost:11434", max_tokens: int = 4096, timeout: float = 120.0):
        super().__init__(api_key, model, base_url, max_tokens, timeout)
        self.endpoint = base_url.rstrip("/") + "/api/chat"

    async def complete(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_predict": self.max_tokens,
                "temperature": 0.2,
            },
        }

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    self.endpoint,
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()

                return LLMResponse(
                    content=data.get("message", {}).get("content", ""),
                    provider="ollama",
                    model=self.model,
                    usage={
                        "prompt_tokens": data.get("prompt_eval_count", 0),
                        "completion_tokens": data.get("eval_count", 0),
                        "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
                    },
                )
        except httpx.HTTPStatusError as e:
            return LLMResponse(
                content="",
                provider="ollama",
                model=self.model,
                error=f"HTTP {e.response.status_code}: {e.response.text[:500]}",
            )
        except Exception as e:
            return LLMResponse(
                content="",
                provider="ollama",
                model=self.model,
                error=str(e),
            )


def get_llm_adapter() -> LLMAdapter:
    """Factory function to get the configured LLM adapter."""
    provider = settings.LLM_PROVIDER.lower()

    if provider == "openai":
        return OpenAICompatibleAdapter(
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            base_url=settings.LLM_BASE_URL,
            max_tokens=settings.LLM_MAX_TOKENS,
        )
    elif provider == "anthropic":
        return AnthropicAdapter(
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            base_url=settings.LLM_BASE_URL,
            max_tokens=settings.LLM_MAX_TOKENS,
        )
    elif provider == "gemini":
        return GeminiAdapter(
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            base_url=settings.LLM_BASE_URL,
            max_tokens=settings.LLM_MAX_TOKENS,
        )
    elif provider == "ollama":
        return OllamaAdapter(
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            base_url=settings.LLM_BASE_URL or "http://localhost:11434",
            max_tokens=settings.LLM_MAX_TOKENS,
        )
    else:
        # Default to OpenAI-compatible for unknown providers
        return OpenAICompatibleAdapter(
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            base_url=settings.LLM_BASE_URL,
            max_tokens=settings.LLM_MAX_TOKENS,
        )


async def complete_llm(prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
    """Convenience function for one-off LLM calls."""
    adapter = get_llm_adapter()
    return await adapter.complete(prompt, system_prompt)