from app.services.compliance import scan_text

BANNED = [
    ("slay", "block"),
    ("guaranteed returns", "block"),
    ("synergy", "warn"),
    ("game-changing", "block"),
]


def test_clean_text_passes():
    r = scan_text("Our fixed deposit has clear terms.", BANNED)
    assert r.passed and r.score == 100 and r.violations == []


def test_block_word_fails_case_insensitive():
    r = scan_text("This card will SLAY.", BANNED)
    assert not r.passed
    assert r.violations[0].word == "slay"
    assert r.violations[0].matched == "SLAY"


def test_no_partial_word_match():
    assert scan_text("The slayer of boring ads.", BANNED).passed


def test_phrase_matches_with_flexible_spacing():
    assert not scan_text("Enjoy guaranteed   returns today", BANNED).passed


def test_hyphen_and_space_variants():
    assert not scan_text("A game changing offer", BANNED).passed
    assert not scan_text("A game-changing offer", BANNED).passed


def test_warn_does_not_fail_but_lowers_score():
    r = scan_text("Great synergy here.", BANNED)
    assert r.passed and r.score == 90
    assert r.violations[0].severity == "warn"


def test_score_floors_at_zero():
    r = scan_text("slay slay slay guaranteed returns", BANNED)
    assert r.score == 0 and not r.passed
