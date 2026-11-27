from pydantic import BaseModel

from app.schemas.brand import BannedWordIn


class Preset(BaseModel):
    id: str
    name: str
    version: int = 1
    source: str
    guidance: str
    terms: tuple[BannedWordIn, ...]
    disclaimer: str = "Editorial guardrails only. Verify individual claims before publication."


CATALOG = {
    preset.id: preset
    for preset in (
        Preset(
            id="india-investment-advice-v1", name="India investment advice",
            source="https://investor.sebi.gov.in/spot-any-scam.html",
            guidance="Avoid promising assured returns on investments.",
            terms=tuple(BannedWordIn(word=word) for word in ("guaranteed returns", "assured returns")),
        ),
        Preset(
            id="india-health-advertising-v1", name="India health advertising",
            source="https://consumeraffairs.gov.in/public/upload/files/CCPA_Notification_1732707665.pdf",
            guidance="Avoid exaggerated efficacy claims. Review health claims for supporting evidence.",
            terms=(BannedWordIn(word="miracle cure", severity="warn"),),
        ),
        Preset(
            id="india-consumer-advertising-v1", name="India consumer advertising",
            source="https://www.ascionline.in/the-asci-code/",
            guidance="Substantiate objective claims and disclose material prices and offer terms.",
            terms=(BannedWordIn(word="free gift", severity="warn"),),
        ),
    )
}


def effective_terms(hub) -> list[tuple[str, str]]:
    if hub is None:
        return []
    words = {item.word: item.severity for item in hub.banned_words}
    for preset_id in hub.preset_ids:
        for term in CATALOG[preset_id].terms:
            if term.word not in words or term.severity == "block":
                words[term.word] = term.severity
    return list(words.items())
