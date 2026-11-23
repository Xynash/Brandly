import time
from typing import Protocol

RETRYABLE_CODES = {429, 500, 502, 503, 504}


class LLMError(Exception):
    """Raised when the model provider fails (missing key, quota, network, blocked output)."""


class LLMProvider(Protocol):
    name: str

    def generate(self, system: str, user: str) -> str: ...


class GeminiProvider:
    name = "gemini"
    retries = 3  # total attempts
    base_delay = 2.0  # seconds; waits 2s, then 4s

    def __init__(self, api_key: str, model: str):
        from google import genai  # imported here so tests and mock mode never need the SDK
        from google.genai import types

        self._client = genai.Client(api_key=api_key)
        self._types = types
        self._model = model

    def generate(self, system: str, user: str) -> str:
        for attempt in range(1, self.retries + 1):
            try:
                resp = self._client.models.generate_content(
                    model=self._model,
                    contents=user,
                    config=self._types.GenerateContentConfig(system_instruction=system),
                )
                break
            except Exception as exc:
                code = getattr(exc, "code", None)
                if code in RETRYABLE_CODES and attempt < self.retries:
                    time.sleep(self.base_delay * attempt)
                    continue
                raise LLMError(f"Gemini request failed: {exc}") from exc
        text = (resp.text or "").strip()
        if not text:
            raise LLMError("Gemini returned no text (it may have been blocked by safety filters)")
        return text


class MockProvider:
    name = "mock"

    def generate(self, system: str, user: str) -> str:
        return f"[mock draft] {user}"


def get_provider() -> LLMProvider:
    from app.core.config import settings  # imported here so unit tests need no .env

    if settings.llm_provider == "mock":
        return MockProvider()
    if not settings.gemini_api_key:
        raise LLMError("GEMINI_API_KEY is not set in backend/.env")
    return GeminiProvider(settings.gemini_api_key, settings.gemini_model)
