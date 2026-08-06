"""Pydantic request/response schemas."""
import uuid
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


# ---- /leads -----------------------------------------------------------

class NormalizeRequest(BaseModel):
    name: str
    email: str
    phone: str | None = None
    company: str | None = None
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


class ConfigStatusResponse(BaseModel):
    openai: bool
    smtp: bool
    slack: bool
    fully_configured: bool


class ConfigSavedResponse(BaseModel):
    key: str
    is_verified: bool = True
