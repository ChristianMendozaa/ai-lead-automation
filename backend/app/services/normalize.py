"""Lead intake normalization: clean fields, dedupe, derive a website to scrape."""
import re
from datetime import datetime, timedelta, timezone

from email_validator import EmailNotValidError, validate_email
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Lead
from app.schemas import NormalizeRequest

# Domains that are never a company website -- skip the scrape step for these.
FREE_EMAIL_DOMAINS = {
    "gmail.com",
    "googlemail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
    "live.com",
    "msn.com",
    "icloud.com",
    "me.com",
    "aol.com",
    "protonmail.com",
    "proton.me",
    "gmx.com",
    "yandex.com",
}

_PHONE_KEEP = re.compile(r"[^0-9+]")


def normalize_email(raw: str) -> str:
    try:
        result = validate_email(raw.strip(), check_deliverability=False)
    except EmailNotValidError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid email: {exc}") from exc
    return result.normalized.lower()


def normalize_phone(raw: str | None) -> str | None:
    if not raw:
        return None
    cleaned = _PHONE_KEEP.sub("", raw).strip()
    return cleaned or None


def normalize_company(raw: str | None) -> str | None:
    if not raw:
        return None
    cleaned = " ".join(raw.split()).strip()
    return cleaned or None


def derive_website_url(email: str) -> str | None:
    domain = email.rsplit("@", 1)[-1].lower()
    if not domain or domain in FREE_EMAIL_DOMAINS:
        return None
    return f"https://{domain}"


def find_recent_duplicate(db: Session, email: str, window_days: int) -> Lead | None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    stmt = (
        select(Lead)
        .where(func.lower(Lead.email) == email, Lead.created_at >= cutoff)
        .order_by(Lead.created_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def normalize_and_create(
    db: Session, payload: NormalizeRequest, *, duplicate_window_days: int
) -> tuple[Lead, bool, str | None]:
    """Returns (lead, is_duplicate, website_url). If a duplicate is found,
    the existing lead row is returned unchanged and no new row is created."""
    email = normalize_email(payload.email)
    phone = normalize_phone(payload.phone)
    company = normalize_company(payload.company)
    website_url = derive_website_url(email)

    existing = find_recent_duplicate(db, email, duplicate_window_days)
    if existing is not None:
        return existing, True, website_url

    lead = Lead(
        name=payload.name.strip(),
        email=email,
        phone=phone,
        company=company,
        raw_payload=payload.model_dump(),
        status="normalized",
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead, False, website_url
