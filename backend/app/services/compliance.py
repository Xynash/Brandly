import re
from dataclasses import dataclass, field


@dataclass
class Violation:
    word: str
    severity: str  # block | warn
    start: int
    end: int
    matched: str


@dataclass
class ScanResult:
    passed: bool
    score: int
    violations: list[Violation] = field(default_factory=list)


def _pattern(phrase: str) -> re.Pattern | None:
    """Whole-word, case-insensitive pattern. Spaces and hyphens inside a phrase are interchangeable."""
    tokens = [t for t in re.split(r"[\s\-]+", phrase.strip()) if t]
    if not tokens:
        return None
    body = r"[\s\-]+".join(re.escape(t) for t in tokens)
    return re.compile(rf"(?<!\w){body}(?!\w)", re.IGNORECASE)


def scan_text(text: str, banned: list[tuple[str, str]]) -> ScanResult:
    """Check text against (word, severity) pairs.

    passed = no 'block' hits. Score v1: 100 - 40 per block hit - 10 per warn hit, floored at 0.
    """
    violations: list[Violation] = []
    for word, severity in banned:
        pattern = _pattern(word)
        if pattern is None:
            continue
        for m in pattern.finditer(text):
            violations.append(Violation(word, severity, m.start(), m.end(), m.group(0)))

    violations.sort(key=lambda v: v.start)
    blocks = sum(1 for v in violations if v.severity == "block")
    warns = sum(1 for v in violations if v.severity == "warn")
    score = max(0, 100 - 40 * blocks - 10 * warns)
    return ScanResult(passed=blocks == 0, score=score, violations=violations)
