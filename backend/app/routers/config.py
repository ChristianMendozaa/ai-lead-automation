"""Setup-wizard config endpoints. Every route here is gated by a shared
X-Setup-Token header -- there's no user account system in v1, just a
secret the Next.js server holds and attaches server-side."""
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.crypto import config_status, get_config, save_config
from app.db import get_db
from app.llm import test_openai_key
from app.schemas import (
    BrandingConfigRequest,
    BrandingPreviewRequest,
    BrandingPreviewResponse,
    BusinessConfigRequest,
    ConfigSavedResponse,
    ConfigStatusResponse,
    OpenAIConfigRequest,
    SlackConfigRequest,
    SmtpConfigRequest,
)
from app.services import mailer, slack
from app.services.email_render import SAMPLE_CONTENT, render_html, resolve_branding

router = APIRouter(prefix="/config", tags=["config"])


def require_setup_token(x_setup_token: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not x_setup_token or x_setup_token != settings.setup_token:
        raise HTTPException(status_code=401, detail="Missing or invalid X-Setup-Token")


@router.post(
    "/openai", response_model=ConfigSavedResponse, dependencies=[Depends(require_setup_token)]
)
def configure_openai(payload: OpenAIConfigRequest, db: Session = Depends(get_db)):
    test_openai_key(payload.api_key)
    save_config(db, "openai", {"api_key": payload.api_key}, verified=True)
    return ConfigSavedResponse(key="openai")


@router.post(
    "/smtp", response_model=ConfigSavedResponse, dependencies=[Depends(require_setup_token)]
)
def configure_smtp(payload: SmtpConfigRequest, db: Session = Depends(get_db)):
    mailer.send_test_email(
        host=payload.host,
        port=payload.port,
        username=payload.username,
        password=payload.password,
        from_address=payload.from_address,
        test_recipient=payload.test_recipient,
    )
    save_config(
        db,
        "smtp",
        {
            "host": payload.host,
            "port": payload.port,
            "username": payload.username,
            "password": payload.password,
            "from_address": payload.from_address,
        },
        verified=True,
    )
    return ConfigSavedResponse(key="smtp")


@router.post(
    "/slack", response_model=ConfigSavedResponse, dependencies=[Depends(require_setup_token)]
)
async def configure_slack(payload: SlackConfigRequest, db: Session = Depends(get_db)):
    await slack.send_test_message(payload.bot_token, payload.channel)
    save_config(
        db, "slack", {"bot_token": payload.bot_token, "channel": payload.channel}, verified=True
    )
    return ConfigSavedResponse(key="slack")


@router.post(
    "/business", response_model=ConfigSavedResponse, dependencies=[Depends(require_setup_token)]
)
def configure_business(payload: BusinessConfigRequest, db: Session = Depends(get_db)):
    # No external service to test against -- just save it.
    save_config(
        db,
        "business",
        {
            "company_name": payload.company_name,
            "sender_name": payload.sender_name or payload.company_name,
            "default_language": payload.default_language or "en",
        },
        verified=True,
    )
    return ConfigSavedResponse(key="business")


@router.get(
    "/branding", response_model=BrandingConfigRequest, dependencies=[Depends(require_setup_token)]
)
def get_branding(db: Session = Depends(get_db)):
    # Unlike the other sections, branding holds no secrets, so it's safe to
    # read back -- needed so the wizard can pre-fill the step instead of
    # wiping unrelated fields on the next full-replace save.
    stored = get_config(db, "branding")
    return BrandingConfigRequest(**resolve_branding(stored))


@router.post(
    "/branding", response_model=ConfigSavedResponse, dependencies=[Depends(require_setup_token)]
)
def configure_branding(payload: BrandingConfigRequest, db: Session = Depends(get_db)):
    # No external service to test against -- just save it. save_config()
    # fully replaces the stored dict, so the wizard must always post the
    # complete branding object (the GET above is what makes that possible).
    save_config(db, "branding", payload.model_dump(), verified=True)
    return ConfigSavedResponse(key="branding")


@router.post(
    "/branding/preview",
    response_model=BrandingPreviewResponse,
    dependencies=[Depends(require_setup_token)],
)
def preview_branding(payload: BrandingPreviewRequest, db: Session = Depends(get_db)):
    # Renders the one real email template with sample content and the
    # *unsaved* branding from the form, so the wizard's live preview can't
    # drift from what a real send would look like.
    business = get_config(db, "business") or {"company_name": "Acme Corp", "sender_name": "Jane"}
    branding = resolve_branding(payload.model_dump())
    html = render_html(SAMPLE_CONTENT, branding=branding, business=business)
    return BrandingPreviewResponse(html=html)


@router.get(
    "/status", response_model=ConfigStatusResponse, dependencies=[Depends(require_setup_token)]
)
def config_status_endpoint(db: Session = Depends(get_db)):
    openai_ok = config_status(db, "openai")
    smtp_ok = config_status(db, "smtp")
    slack_ok = config_status(db, "slack")
    business_ok = config_status(db, "business")
    branding_ok = config_status(db, "branding")
    return ConfigStatusResponse(
        openai=openai_ok,
        smtp=smtp_ok,
        slack=slack_ok,
        business=business_ok,
        branding=branding_ok,
        # Branding is optional -- it deliberately doesn't gate "fully configured".
        fully_configured=openai_ok and smtp_ok and slack_ok and business_ok,
    )
