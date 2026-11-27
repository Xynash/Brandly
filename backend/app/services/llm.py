import time
from typing import Protocol

import httpx

RETRYABLE_CODES = {429, 500, 502, 503, 504}
MODEL_UNAVAILABLE_CODES = {404}  # model retired or not available to this key: try the next model


class LLMError(Exception):
    """Raised when the model provider fails (missing key, quota, network, blocked output)."""


class LLMProvider(Protocol):
    name: str

    def generate(self, system: str, user: str) -> str: ...


class GeminiProvider:
    name = "gemini"
    attempts_per_model = 2
    base_delay = 2.0  # seconds to wait before the second attempt on the same model
    total_budget = 45.0  # stop retrying once this many seconds have passed

    def __init__(self, api_key: str, model: str, fallback_model: str = "", timeout_seconds: int = 25):
        from google import genai  # imported here so tests and mock mode never need the SDK
        from google.genai import types

        self._client = genai.Client(api_key=api_key)
        self._types = types
        self._timeout_ms = int(timeout_seconds * 1000)
        self._models = [model]
        if fallback_model and fallback_model != model:
            self._models.append(fallback_model)

    def generate(self, system: str, user: str) -> str:
        start = time.monotonic()
        resp = None
        last_error: str | None = None
        for model in self._models:
            for attempt in range(1, self.attempts_per_model + 1):
                try:
                    resp = self._client.models.generate_content(
                        model=model,
                        contents=user,
                        config=self._types.GenerateContentConfig(
                            system_instruction=system,
                            http_options=self._types.HttpOptions(timeout=self._timeout_ms),
                        ),
                    )
                    break
                except Exception as exc:
                    code = getattr(exc, "code", None)
                    error = f"error {code}" if isinstance(code, int) else "connection error"
                    if code in MODEL_UNAVAILABLE_CODES:
                        last_error = error
                        break  # no point retrying this model; move on to the next one
                    if code not in RETRYABLE_CODES:
                        earlier = f" (earlier: {last_error})" if last_error else ""
                        raise LLMError(f"Gemini request failed: {error}{earlier}") from exc
                    last_error = error
                    if time.monotonic() - start > self.total_budget:
                        raise LLMError(
                            f"Gemini request failed: gave up after {self.total_budget:.0f}s ({error})"
                        ) from exc
                    if attempt < self.attempts_per_model:
                        time.sleep(self.base_delay)
            if resp is not None:
                break
        if resp is None:
            raise LLMError(f"Gemini request failed: {last_error}")
        text = (resp.text or "").strip()
        if not text:
            raise LLMError("Gemini returned no text (it may have been blocked by safety filters)")
        return text


class MockProvider:
    name = "mock"

    def generate(self, system: str, user: str) -> str:
        return f"[mock draft] {user}"


class HTTPProvider:
    def __init__(self, name: str, api_key: str, model: str, timeout_seconds: int):
        self.name = name
        self._key = api_key
        self._model = model
        self._timeout = timeout_seconds

    def generate(self, system: str, user: str) -> str:
        if self.name == "openai":
            url = "https://api.openai.com/v1/responses"
            headers = {"Authorization": f"Bearer {self._key}"}
            body = {"model": self._model, "instructions": system, "input": user,
                    "max_output_tokens": 4096, "store": False}
        else:
            url = "https://api.anthropic.com/v1/messages"
            headers = {"x-api-key": self._key, "anthropic-version": "2023-06-01"}
            body = {"model": self._model, "system": system, "max_tokens": 4096,
                    "messages": [{"role": "user", "content": user}]}
        try:
            response = httpx.post(url, headers=headers, json=body, timeout=self._timeout, trust_env=False)
            response.raise_for_status()
            payload = response.json()
            if self.name == "openai":
                parts = (
                    block["text"] for item in payload["output"] if item["type"] == "message"
                    for block in item["content"] if block["type"] == "output_text"
                )
            else:
                parts = (block["text"] for block in payload["content"] if block["type"] == "text")
            draft = "\n".join(parts).strip()
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise LLMError(f"{self.name} request failed") from exc
        if not draft:
            raise LLMError(f"{self.name} returned no text")
        return draft


def get_provider(api_key: str | None = None) -> LLMProvider:
    from app.core.config import settings

    provider = settings.llm_provider
    if provider == "mock":
        return MockProvider()
    key = api_key or getattr(settings, f"{provider}_api_key")
    model = getattr(settings, f"{provider}_model")
    if not key or not model:
        raise LLMError(f"{provider} credentials or model are not configured")
    if provider == "gemini":
        return GeminiProvider(key, model, settings.gemini_fallback_model, settings.gemini_timeout_seconds)
    return HTTPProvider(provider, key, model, settings.llm_timeout_seconds)
