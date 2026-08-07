"""Pydantic request/response schemas."""
import re
import uuid
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---- /leads -----------------------------------------------------------

class NormalizeRequest(BaseModel):
    name: str
    email: str
    phone: str | None = None
    company: str | None = None
    # Optional: lets leads submitted from a personal email address (Gmail,
    # etc.) still get real website enrichment, since the domain-derived
    # guess only works for business email addresses.
    website: str | None = None
    message: str | None = None
    # allow any extra fields the form sends through without choking
    model_config = {"extra": "allow"}


class NormalizeResponse(BaseModel):
    lead_id: uuid.UUID
    is_duplicate: bool
    website_url: str | None
    name: str
    email: str
    phone: str | None
    company: str | None


class EnrichRequest(BaseModel):
    scraped_html: str = ""


class EnrichResponse(BaseModel):
    lead_id: uuid.UUID
    enrichment: dict
    status: str


class DraftResponse(BaseModel):
    lead_id: uuid.UUID
    draft_subject: str
    draft_body: str
    draft_language: str | None = None
    status: str


class RequestApprovalRequest(BaseModel):
    resume_url: str


class RequestApprovalResponse(BaseModel):
    lead_id: uuid.UUID
    slack_message_ts: str | None = None


class SendResponse(BaseModel):
    lead_id: uuid.UUID
    status: str


class StatusUpdateRequest(BaseModel):
    status: Literal["sent", "rejected", "failed"]


# ---- /config ------------------------------------------------------------

class OpenAIConfigRequest(BaseModel):
    api_key: str


class SmtpConfigRequest(BaseModel):
    host: str
    port: int = 587
    username: str
    password: str
    from_address: EmailStr
    test_recipient: EmailStr


class SlackConfigRequest(BaseModel):
    bot_token: str
    channel: str


class BusinessConfigRequest(BaseModel):
    company_name: str
    # Who the drafted emails are signed as. Defaults to the company name
    # itself if left blank (e.g. "The Acme Corp Team").
    sender_name: str | None = None
    # Used only when a lead's submission gives the draft prompt no language
    # signal (no free-text message, no website enrichment language).
    default_language: str = "en"


_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def _validate_http_url(value: str) -> str:
    """Shared guard for every branding URL field: empty is fine (the field
    is optional), but a non-empty value must be http(s) -- this is what
    keeps a javascript: URL out of an <a href> or <img src> in the
    rendered email."""
    value = (value or "").strip()
    if not value:
        return ""
    scheme = urlsplit(value).scheme.lower()
    if scheme not in ("http", "https"):
        raise ValueError("must be an http:// or https:// URL")
    return value


class SocialLink(BaseModel):
    label: str = ""
    url: str = ""

    @field_validator("url")
    @classmethod
    def _url_is_http(cls, v: str) -> str:
        return _validate_http_url(v)


class BrandingConfigRequest(BaseModel):
    # Visual identity
    primary_color: str = "#0f172a"
    accent_color: str = "#2563eb"
    background_color: str = "#f8fafc"
    text_color: str = "#0f172a"
    logo_url: str = ""
    font_family: Literal["sans", "serif", "mono", "rounded"] = "sans"

    # Voice, fed into the draft prompt so copy matches the brand
    brand_tone: Literal["professional", "friendly", "bold", "minimal", "luxury"] = "professional"
    industry: str = ""
    description: str = ""
    value_proposition: str = ""

    # Call-to-action + signature block
    cta_label: str = ""
    cta_url: str = ""
    sender_title: str = ""
    sender_phone: str = ""
    website_url: str = ""

    # Footer / compliance
    tagline: str = ""
    address: str = ""
    social_links: list[SocialLink] = []
    unsubscribe_line: str = ""

    @field_validator("primary_color", "accent_color", "background_color", "text_color")
    @classmethod
    def _color_is_hex(cls, v: str) -> str:
        if not _HEX_COLOR_RE.match(v or ""):
            raise ValueError('must be a hex color like "#0f172a"')
        return v

    @field_validator("logo_url", "cta_url", "website_url")
    @classmethod
    def _url_is_http(cls, v: str) -> str:
        return _validate_http_url(v)


class ConfigStatusResponse(BaseModel):
    openai: bool
    smtp: bool
    slack: bool
    business: bool
    branding: bool
    fully_configured: bool


class ConfigSavedResponse(BaseModel):
    key: str
    is_verified: bool = True


class BrandingPreviewRequest(BrandingConfigRequest):
    pass


class BrandingPreviewResponse(BaseModel):
    html: str
