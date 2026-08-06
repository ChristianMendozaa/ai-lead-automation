"""Fernet-based encryption for credentials stored in app_config, plus
thin CRUD helpers over that table so routers/services don't touch
SQLAlchemy directly for config reads/writes."""
import json

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AppConfig


class DecryptionError(RuntimeError):
    """Raised when stored config can't be decrypted (e.g. key rotated)."""


def _fernet() -> Fernet:
    return Fernet(get_settings().app_encryption_key.encode())


def encrypt_dict(data: dict) -> bytes:
    payload = json.dumps(data).encode()
    return _fernet().encrypt(payload)


def decrypt_dict(token: bytes) -> dict:
    try:
        payload = _fernet().decrypt(bytes(token))
    except InvalidToken as exc:
        raise DecryptionError("Could not decrypt stored credential") from exc
    return json.loads(payload)


def save_config(db: Session, key: str, value: dict, *, verified: bool) -> AppConfig:
    row = db.get(AppConfig, key)
    encrypted = encrypt_dict(value)
    if row is None:
        row = AppConfig(key=key, value_encrypted=encrypted, is_verified=verified)
        db.add(row)
    else:
        row.value_encrypted = encrypted
        row.is_verified = verified
    db.commit()
    db.refresh(row)
    return row


def get_config(db: Session, key: str) -> dict | None:
    """Returns the decrypted value dict, or None if not configured/verified."""
    row = db.get(AppConfig, key)
    if row is None or not row.is_verified:
        return None
    return decrypt_dict(row.value_encrypted)


def config_status(db: Session, key: str) -> bool:
    row = db.get(AppConfig, key)
    return bool(row and row.is_verified)
