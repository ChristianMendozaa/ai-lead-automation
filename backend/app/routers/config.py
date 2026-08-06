"""Setup-wizard config endpoints. Every route here is gated by a shared
X-Setup-Token header -- there's no user account system in v1, just a
secret the Next.js server holds and attaches server-side."""
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.crypto import config_status, save_config
from app.db import get_db
from app.llm import test_openai_key
from app.schemas import (
    ConfigSavedResponse,
    ConfigStatusResponse,
    OpenAIConfigRequest,
    SlackConfigRequest,
    SmtpConfigRequest,
)
from app.services import mailer, slack

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


@router.get(
    "/status", response_model=ConfigStatusResponse, dependencies=[Depends(require_setup_token)]
)
def config_status_endpoint(db: Session = Depends(get_db)):
    openai_ok = config_status(db, "openai")
    smtp_ok = config_status(db, "smtp")
    slack_ok = config_status(db, "slack")
    return ConfigStatusResponse(
        openai=openai_ok,
        smtp=smtp_ok,
        slack=slack_ok,
        fully_configured=openai_ok and smtp_ok and slack_ok,
    )
