from app.models import Client
from app.services.presets import CATALOG, effective_terms
from app.services.prompt_builder import HubContext


def build_context(client: Client) -> tuple[HubContext, list[tuple[str, str]]]:
    """One client's hub as (prompt context, banned words as (word, severity) pairs)."""
    hub = client.hub
    words = effective_terms(hub)
    guidance = [CATALOG[item].guidance for item in hub.preset_ids] if hub else []
    dos = "\n".join(filter(None, [hub.dos if hub else "", *guidance]))
    ctx = HubContext(
        client_name=client.name,
        industry=client.industry,
        tone_description=hub.tone_description if hub else "",
        audience=hub.audience if hub else "",
        dos=dos,
        donts=hub.donts if hub else "",
        sample_content=hub.sample_content if hub else "",
        banned_block=[word for word, severity in words if severity == "block"],
        banned_warn=[word for word, severity in words if severity == "warn"],
    )
    return ctx, words
