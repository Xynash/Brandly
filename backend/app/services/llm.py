from typing import Protocol


class LLMError(Exception):
    """Raised when the model provider fails (missing key, quota, network, blocked output)."""


class LLMProvider(Protocol):
    name: str

    def generate(self, system: str, user: str) -> str: ...


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str):
        from google import genai  # imported here so tests and mock mode never need the SDK
        from google.genai import types

        self._client = genai.Client(api_key=api_key)
        self._types = types
        self._model = model

    def generate(self, system: str, user: str) -> str:
        try:
            resp = self._client.models.generate_content(
                model=self._model,
                contents=user,
                config=self._types.GenerateContentConfig(system_instruction=system),
            )
        except Exception as exc:
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
