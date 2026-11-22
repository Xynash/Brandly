from app.services.generation import generate_checked
from app.services.prompt_builder import HubContext

BANNED = [("slay", "block"), ("synergy", "warn")]
CTX = HubContext(client_name="Acme", banned_block=["slay"], banned_warn=["synergy"])


class FakeProvider:
    name = "fake"

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def generate(self, system, user):
        self.calls.append((system, user))
        return self.replies.pop(0)


def test_clean_first_draft_is_delivered():
    p = FakeProvider(["A calm, clear announcement."])
    r = generate_checked(p, CTX, "Write a post", BANNED)
    assert r.attempts == 1 and not r.flagged and r.scan.passed
    assert len(p.calls) == 1


def test_violation_triggers_one_retry_with_stricter_prompt():
    p = FakeProvider(["This will slay!", "A calm, clear announcement."])
    r = generate_checked(p, CTX, "Write a post", BANNED)
    assert r.attempts == 2 and not r.flagged
    assert r.text == "A calm, clear announcement."
    assert '"slay"' in p.calls[1][0]
    assert '"slay"' not in p.calls[0][0]


def test_second_failure_is_flagged_not_looped():
    p = FakeProvider(["slay one", "slay two", "must never be used"])
    r = generate_checked(p, CTX, "Write a post", BANNED)
    assert r.flagged and not r.scan.passed and r.attempts == 2
    assert len(p.calls) == 2


def test_warn_only_does_not_retry():
    p = FakeProvider(["Great synergy."])
    r = generate_checked(p, CTX, "Write a post", BANNED)
    assert r.attempts == 1 and not r.flagged and r.scan.score == 90
