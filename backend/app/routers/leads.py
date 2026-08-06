"""Lead pipeline endpoints, called by n8n in order as the workflow runs."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.crypto import get_config
from app.db import get_db
from app.llm import get_provider
from app.models import Lead
from app.schemas import (
    DraftResponse,
    EnrichRequest,
    EnrichResponse,
    NormalizeRequest,
    NormalizeResponse,
    RequestApprovalRequest,
    RequestApprovalResponse,
    SendResponse,
    StatusUpdateRequest,
)
from app.services import draft as draft_service
from app.services import enrich as enrich_service
from app.services import mailer, slack
from app.services import normalize as normalize_service

router = APIRouter(prefix="/leads", tags=["leads"])


def _get_lead_or_404(db: Session, lead_id: uuid.UUID) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.post("/normalize", response_model=NormalizeResponse)
def normalize_lead(payload: NormalizeRequest, db: Session = Depends(get_db)):
    settings = get_settings()
    lead, is_duplicate, website_url = normalize_service.normalize_and_create(
        db, payload, duplicate_window_days=settings.duplicate_window_days
    )
    return NormalizeResponse(
        lead_id=lead.id,
        is_duplicate=is_duplicate,
        website_url=website_url,
        name=lead.name,
        email=lead.email,
        phone=lead.phone,
        company=lead.company,
    )


@router.post("/{lead_id}/enrich", response_model=EnrichResponse)
async def enrich_lead(lead_id: uuid.UUID, payload: EnrichRequest, db: Session = Depends(get_db)):
    lead = _get_lead_or_404(db, lead_id)

    if payload.scraped_html.strip():
        provider = get_provider(db)
        enrichment = await enrich_service.enrich_from_html(provider, payload.scraped_html)
    else:
        enrichment = {"available": False}

    lead.enrichment = enrichment
    lead.status = "enriched"
    db.commit()
    db.refresh(lead)
    return EnrichResponse(lead_id=lead.id, enrichment=lead.enrichment, status=lead.status)


@router.post("/{lead_id}/draft", response_model=DraftResponse)
async def draft_lead(lead_id: uuid.UUID, db: Session = Depends(get_db)):
    lead = _get_lead_or_404(db, lead_id)
    provider = get_provider(db)

    business = get_config(db, "business")
    if business is None:
        raise HTTPException(status_code=409, detail="Business info is not configured yet.")

    result = await draft_service.draft_email(
        provider,
        lead,
        sender_name=business["sender_name"],
        company_name=business["company_name"],
    )
    lead.draft_subject = result["subject"]
    lead.draft_body = result["body"]
    lead.status = "draft_ready"
    db.commit()
    db.refresh(lead)
    return DraftResponse(
        lead_id=lead.id,
        draft_subject=lead.draft_subject,
        draft_body=lead.draft_body,
        status=lead.status,
    )


@router.post("/{lead_id}/request-approval", response_model=RequestApprovalResponse)
async def request_approval(
    lead_id: uuid.UUID, payload: RequestApprovalRequest, db: Session = Depends(get_db)
):
    lead = _get_lead_or_404(db, lead_id)
    if not lead.draft_subject or not lead.draft_body:
        raise HTTPException(status_code=409, detail="Lead has no draft to approve yet")

    cfg = get_config(db, "slack")
    if cfg is None:
        raise HTTPException(status_code=409, detail="Slack is not configured yet.")

    ts = await slack.send_approval_request(
        cfg["bot_token"],
        cfg["channel"],
        lead_name=lead.name,
        lead_email=lead.email,
        company=lead.company,
        subject=lead.draft_subject,
        body=lead.draft_body,
        resume_url=payload.resume_url,
    )
    return RequestApprovalResponse(lead_id=lead.id, slack_message_ts=ts)


@router.post("/{lead_id}/send", response_model=SendResponse)
def send_lead_email(lead_id: uuid.UUID, db: Session = Depends(get_db)):
    lead = _get_lead_or_404(db, lead_id)
    if not lead.draft_subject or not lead.draft_body:
        raise HTTPException(status_code=409, detail="Lead has no draft to send")

    cfg = get_config(db, "smtp")
    if cfg is None:
        raise HTTPException(status_code=409, detail="SMTP is not configured yet.")

    try:
        mailer.send_outreach_email(
            host=cfg["host"],
            port=cfg["port"],
            username=cfg["username"],
            password=cfg["password"],
            from_address=cfg["from_address"],
            to_address=lead.email,
            subject=lead.draft_subject,
            body=lead.draft_body,
        )
    except HTTPException:
        lead.status = "failed"
        db.commit()
        raise

    lead.status = "sent"
    db.commit()
    db.refresh(lead)
    return SendResponse(lead_id=lead.id, status=lead.status)


@router.patch("/{lead_id}/status", response_model=SendResponse)
def update_status(lead_id: uuid.UUID, payload: StatusUpdateRequest, db: Session = Depends(get_db)):
    lead = _get_lead_or_404(db, lead_id)
    lead.status = payload.status
    db.commit()
    db.refresh(lead)
    return SendResponse(lead_id=lead.id, status=lead.status)
