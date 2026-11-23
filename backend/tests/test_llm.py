import pytest

from app.services.llm import GeminiProvider, LLMError


class Boom(Exception):
    def __init__(self, code):
        super().__init__(f"error {code}")
        self.code = code


class FakeModels:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.models_used = []

    @property
    def calls(self):
        return len(self.models_used)

    def generate_content(self, **kwargs):
        self.models_used.append(kwargs["model"])
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return type("Resp", (), {"text": outcome})()


class FakeTypes:
    @staticmethod
    def GenerateContentConfig(**kwargs):
        return kwargs


def make_provider(outcomes, models=("m1",)):
    p = GeminiProvider.__new__(GeminiProvider)  # skip __init__ so no SDK or key is needed
    p._client = type("Client", (), {"models": FakeModels(outcomes)})()
    p._types = FakeTypes
    p._models = list(models)
    p.base_delay = 0
    return p


def test_retries_a_503_then_succeeds():
    p = make_provider([Boom(503), "all good"])
    assert p.generate("sys", "user") == "all good"
    assert p._client.models.calls == 2


def test_falls_back_to_second_model_after_repeated_503():
    p = make_provider([Boom(503), Boom(503), "from fallback"], models=("m1", "m2"))
    assert p.generate("sys", "user") == "from fallback"
    assert p._client.models.models_used == ["m1", "m1", "m2"]


def test_gives_up_when_every_model_fails():
    p = make_provider([Boom(503)] * 4, models=("m1", "m2"))
    with pytest.raises(LLMError):
        p.generate("sys", "user")
    assert p._client.models.calls == 4


def test_does_not_retry_a_client_error():
    p = make_provider([Boom(400)], models=("m1", "m2"))
    with pytest.raises(LLMError):
        p.generate("sys", "user")
    assert p._client.models.calls == 1
