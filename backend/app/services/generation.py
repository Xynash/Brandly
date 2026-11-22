from dataclasses import dataclass

from app.services.compliance import ScanResult, scan_text
from app.services.llm import LLMProvider
from app.services.prompt_builder import HubContext, build_prompt


@dataclass
class GenerationResult:
    text: str
    scan: ScanResult
    attempts: int
    flagged: bool


def _retry_instruction(scan: ScanResult) -> str:
    words = sorted({v.word for v in scan.violations if v.severity == "block"})
    listed = ", ".join(f'"{w}"' for w in words)
    return (
        "IMPORTANT: your previous draft broke the rules by using these forbidden words or "
        f"phrases: {listed}. Rewrite the content without them, using different wording."
    )


def generate_checked(
    provider: LLMProvider,
    ctx: HubContext,
    task: str,
    banned: list[tuple[str, str]],
    max_attempts: int = 2,
) -> GenerationResult:
    """Generate, scan, and retry once with a stricter prompt. Still failing means flagged for a human."""
    extra: str | None = None
    for attempt in range(1, max_attempts + 1):
        built = build_prompt(ctx, task, extra_instruction=extra)
        text = provider.generate(built.system, built.user)
        result = scan_text(text, banned)
        if result.passed:
            return GenerationResult(text, result, attempt, flagged=False)
        extra = _retry_instruction(result)
    return GenerationResult(text, result, max_attempts, flagged=True)
