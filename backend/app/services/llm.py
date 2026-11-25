import time
from typing import Protocol

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
        last_exc: Exception | None = None
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
                    if code in MODEL_UNAVAILABLE_CODES:
                        last_exc = exc
                        break  # no point retrying this model; move on to the next one
                    if code not in RETRYABLE_CODES:
                        earlier = f" (earlier error: {last_exc})" if last_exc else ""
                        raise LLMError(f"Gemini request failed: {exc}{earlier}") from exc
                    last_exc = exc
                    if time.monotonic() - start > self.total_budget:
                        raise LLMError(
                            f"Gemini request failed: gave up after {self.total_budget:.0f}s ({exc})"
                        ) from exc
                    if attempt < self.attempts_per_model:
                        time.sleep(self.base_delay)
            if resp is not None:
                break
        if resp is None:
            raise LLMError(f"Gemini request failed: {last_exc}") from last_exc
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
    return GeminiProvider(
        settings.gemini_api_key,
        settings.gemini_model,
        settings.gemini_fallback_model,
        settings.gemini_timeout_seconds,
    )
