"""Seed demo data. Safe to re-run:  python -m app.seed"""
from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import Agency, BannedWord, BrandHub, Client

AGENCY_NAME = "Brandly Seed Agency"

CLIENTS = [
    {
        "name": "FinBank",
        "industry": "fintech",
        "hub": {
            "tone_description": "Formal, trustworthy and precise. Plain language, no jargon, calm confidence.",
            "audience": "Salaried professionals aged 25 to 45 comparing credit cards, savings and loans.",
            "dos": "State that terms and conditions apply. Mention that rates and fees are subject to change. Use full sentences.",
            "donts": "No slang. No emojis. No promises about returns, approvals or savings. No urgency or fear tactics.",
            "sample_content": "Your savings deserve a plan. Learn how our fixed deposit works, with clear terms and no surprises.",
        },
        "banned": [
            ("guaranteed returns", "block"), ("slay", "block"), ("no cap", "block"),
            ("risk-free", "block"), ("get rich", "block"),
            ("synergy", "warn"), ("game-changing", "warn"),
        ],
    },
    {
        "name": "ZestWear",
        "industry": "d2c apparel",
        "hub": {
            "tone_description": "Witty, casual and upbeat. Short punchy lines, playful wordplay, light Gen Z slang is welcome. Sounds like a funny friend with great style.",
            "audience": "Urban shoppers aged 18 to 30 who buy fashion on Instagram and care about style, comfort and price.",
            "dos": "Use 1 or 2 emojis per post. Keep it under 60 words. Lead with a hook. End with a clear call to action.",
            "donts": "No corporate language. No long paragraphs. No mocking other brands. Do not invent discount percentages or dates.",
            "sample_content": "New drop alert. Your wardrobe called, it wants fresh energy. Tap the link and pick your fit.",
        },
        "banned": [
            ("cheap", "block"), ("fast fashion", "block"),
            ("revolutionary", "warn"), ("game-changing", "warn"),
        ],
    },
    {
        "name": "CarePlus Hospital",
        "industry": "healthcare",
        "hub": {
            "tone_description": "Warm, calm and reassuring. Simple, respectful language a family member could understand. Compassionate without being dramatic.",
            "audience": "Patients and their families across all ages, often anxious and looking for clear, trustworthy information.",
            "dos": "Encourage readers to consult a qualified doctor. Use plain words instead of medical jargon. Mention that outcomes vary from patient to patient.",
            "donts": "No diagnoses or medical advice. No guarantees of outcomes. No before and after claims. No fear tactics. Do not claim to be the best or number one.",
            "sample_content": "Our care team is here for you and your family, every step of the way. Book a consultation to talk with a specialist.",
        },
        "banned": [
            ("miracle cure", "block"), ("100% cure", "block"), ("guaranteed results", "block"),
            ("painless", "warn"), ("best hospital", "warn"),
        ],
    },
]


def get_or_create_agency(db) -> Agency:
    agency = db.scalar(select(Agency).where(Agency.name == AGENCY_NAME))
    if agency is None:
        agency = Agency(name=AGENCY_NAME)
        db.add(agency)
        db.flush()
    return agency


def upsert_client(db, agency: Agency, spec: dict) -> Client:
    client = db.scalar(
        select(Client).where(Client.agency_id == agency.id, Client.name == spec["name"])
    )
    if client is None:
        client = Client(agency_id=agency.id, name=spec["name"], industry=spec["industry"])
        db.add(client)
    client.industry = spec["industry"]
    if client.hub is None:
        client.hub = BrandHub()
    for field, value in spec["hub"].items():
        setattr(client.hub, field, value)

    client.hub.banned_words.clear()
    db.flush()  # apply the deletes before inserting, so the unique (hub, word) rule never trips
    for word, severity in spec["banned"]:
        client.hub.banned_words.append(BannedWord(word=word.strip().lower(), severity=severity))
    return client


def main() -> None:
    with SessionLocal() as db:
        agency = get_or_create_agency(db)
        for spec in CLIENTS:
            upsert_client(db, agency, spec)
        db.commit()

        print(f"Agency: {agency.name}  id={agency.id}")
        for c in db.scalars(select(Client).where(Client.agency_id == agency.id).order_by(Client.name)):
            print(f"  {c.name:<20} {c.industry:<14} {c.id}")


if __name__ == "__main__":
    main()
