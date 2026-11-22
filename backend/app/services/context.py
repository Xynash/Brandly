from app.models import Client
from app.services.prompt_builder import HubContext


def build_context(client: Client) -> tuple[HubContext, list[tuple[str, str]]]:
    """One client's hub as (prompt context, banned words as (word, severity) pairs)."""
    hub = client.hub
    words = hub.banned_words if hub else []
    ctx = HubContext(
        client_name=client.name,
        industry=client.industry,
        tone_description=hub.tone_description if hub else "",
        audience=hub.audience if hub else "",
        dos=hub.dos if hub else "",
        donts=hub.donts if hub else "",
        sample_content=hub.sample_content if hub else "",
        banned_block=[w.word for w in words if w.severity == "block"],
        banned_warn=[w.word for w in words if w.severity == "warn"],
    )
    return ctx, [(w.word, w.severity) for w in words]
