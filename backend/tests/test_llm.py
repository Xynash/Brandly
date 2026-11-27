import httpx
import pytest

from app.services.llm import GeminiProvider, HTTPProvider, LLMError


class Boom(Exception):
    def __init__(self, code):
        super().__init__(f"error {code}")
        self.code = code


class FakeModels:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.kwargs = []

    @property
    def models_used(self):
        return [k["model"] for k in self.kwargs]

    @property
    def calls(self):
        return len(self.kwargs)

    def generate_content(self, **kwargs):
        self.kwargs.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return type("Resp", (), {"text": outcome})()


class FakeTypes:
    @staticmethod
    def GenerateContentConfig(**kwargs):
        return kwargs

    @staticmethod
    def HttpOptions(**kwargs):
        return kwargs


def make_provider(outcomes, models=("m1",)):
    p = GeminiProvider.__new__(GeminiProvider)  # skip __init__ so no SDK or key is needed
    p._client = type("Client", (), {"models": FakeModels(outcomes)})()
    p._types = FakeTypes
    p._models = list(models)
    p._timeout_ms = 25000
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


def test_every_request_carries_a_timeout():
    p = make_provider(["ok"])
    p.generate("sys", "user")
    config = p._client.models.kwargs[0]["config"]
    assert config["http_options"] == {"timeout": 25000}
    assert config["system_instruction"] == "sys"


def test_stops_retrying_once_the_time_budget_is_spent():
    p = make_provider([Boom(503), "never reached"], models=("m1", "m2"))
    p.total_budget = -1
    with pytest.raises(LLMError) as exc:
        p.generate("sys", "user")
    assert "gave up" in str(exc.value)
    assert p._client.models.calls == 1


def test_a_retired_model_falls_through_to_the_next_model_without_retrying():
    p = make_provider([Boom(404), "from fallback"], models=("m1", "m2"))
    assert p.generate("sys", "user") == "from fallback"
    assert p._client.models.models_used == ["m1", "m2"]


def test_fails_clearly_when_every_model_is_unavailable():
    p = make_provider([Boom(404), Boom(404)], models=("m1", "m2"))
    with pytest.raises(LLMError) as exc:
        p.generate("sys", "user")
    assert "error 404" in str(exc.value)
    assert p._client.models.calls == 2


def test_a_later_hard_error_still_mentions_the_earlier_failure():
    p = make_provider([Boom(503), Boom(503), Boom(400)], models=("m1", "m2"))
    with pytest.raises(LLMError) as exc:
        p.generate("sys", "user")
    assert "error 400" in str(exc.value) and "error 503" in str(exc.value)


@pytest.mark.parametrize(("provider", "path", "payload"), [
    ("openai", "/v1/responses", {
        "output": [{"type": "reasoning"}, {"type": "message", "content": [
            {"type": "output_text", "text": "Checked copy"},
        ]}],
    }),
    ("anthropic", "/v1/messages", {
        "content": [{"type": "text", "text": "Checked copy"}],
    }),
])
def test_http_provider_sends_instructions_and_extracts_text(monkeypatch, provider, path, payload):
    def post(url, *, headers, json, timeout, trust_env):
        assert url.endswith(path)
        assert json["model"] == "example-model"
        assert timeout == 7 and trust_env is False
        if provider == "openai":
            assert headers["Authorization"] == "Bearer dummy"
            assert json["instructions"] == "brand rules" and json["input"] == "task"
        else:
            assert headers["x-api-key"] == "dummy"
            assert json["system"] == "brand rules" and json["messages"][0]["content"] == "task"
        return httpx.Response(200, json=payload, request=httpx.Request("POST", url))

    monkeypatch.setattr("app.services.llm.httpx.post", post)
    assert HTTPProvider(provider, "dummy", "example-model", 7).generate("brand rules", "task") == "Checked copy"
