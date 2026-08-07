import pytest

from app.models import Lead
from app.services.draft import draft_email

BUSINESS = {"company_name": "Acme Corp", "sender_name": "Jane", "default_language": "fr"}
BRANDING = {"brand_tone": "friendly", "cta_url": "https://cal.com/jane", "cta_label": "Book a call"}


class FakeProvider:
    def __init__(self, response: dict):
        self._response = response
        self.last_system: str | None = None
        self.last_user: str | None = None

    async def complete_json(self, *, system: str, user: str) -> dict:
        self.last_system = system
        self.last_user = user
        return self._response

    async def complete_text(self, *, system: str, user: str) -> str:
        raise NotImplementedError


def _lead(**overrides) -> Lead:
    lead = Lead(name="María López", email="maria@example.com")
    for key, value in overrides.items():
        setattr(lead, key, value)
    return lead


@pytest.mark.asyncio
async def test_draft_email_structured_response_passthrough():
    provider = FakeProvider(
        {
            "language": "es",
            "subject": "Hola María",
            "preheader": "Un mensaje breve",
            "greeting": "Hola María,",
            "paragraphs": ["Gracias por tu mensaje."],
            "cta_label": "Agendar una llamada",
            "signoff": "Un saludo,",
        }
    )
    lead = _lead()
    result = await draft_email(provider, lead, business=BUSINESS, branding=BRANDING)
    assert result["language"] == "es"
    assert result["subject"] == "Hola María"
    assert result["paragraphs"] == ["Gracias por tu mensaje."]
    assert result["cta_label"] == "Agendar una llamada"


@pytest.mark.asyncio
async def test_draft_email_legacy_body_response_splits_into_paragraphs():
    provider = FakeProvider(
        {
            "language": "en",
            "subject": "Hi",
            "body": "First paragraph.\n\nSecond paragraph.",
        }
    )
    lead = _lead()
    result = await draft_email(provider, lead, business=BUSINESS, branding=BRANDING)
    assert result["paragraphs"] == ["First paragraph.", "Second paragraph."]


@pytest.mark.asyncio
async def test_draft_email_falls_back_to_business_default_language_when_missing():
    provider = FakeProvider({"subject": "Hi", "paragraphs": ["Hello."]})
    lead = _lead()
    result = await draft_email(provider, lead, business=BUSINESS, branding=BRANDING)
    assert result["language"] == "fr"


@pytest.mark.asyncio
async def test_draft_email_context_includes_fallback_language_and_brand_tone():
    provider = FakeProvider({"subject": "Hi", "paragraphs": ["Hello."]})
    lead = _lead()
    await draft_email(provider, lead, business=BUSINESS, branding=BRANDING)
    assert "fr" in provider.last_user
    assert "friendly" in provider.last_user


@pytest.mark.asyncio
async def test_draft_email_omits_cta_instruction_when_no_cta_url_configured():
    provider = FakeProvider({"subject": "Hi", "paragraphs": ["Hello."]})
    lead = _lead()
    await draft_email(provider, lead, business=BUSINESS, branding={})
    assert "leave cta_label empty" in provider.last_user
