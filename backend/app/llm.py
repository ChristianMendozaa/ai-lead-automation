"""Thin LLM provider interface. OpenAI is the only implementation for v1;
adding another provider later means one new class + one branch in
get_provider() -- nothing else in the app should import openai directly.
"""
import json
from typing import Protocol

from fastapi import HTTPException
from openai import APIError, AuthenticationError, OpenAI
from sqlalchemy.orm import Session

from app.config import get_settings
from app.crypto import get_config


class LLMProvider(Protocol):
    async def complete_json(self, *, system: str, user: str) -> dict:
        """Return a parsed JSON object from the model's response."""
        ...

    async def complete_text(self, *, system: str, user: str) -> str:
        """Return a plain text response."""
        ...


class OpenAIProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = OpenAI(api_key=api_key)
        self._model = model

    async def complete_json(self, *, system: str, user: str) -> dict:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        content = resp.choices[0].message.content or "{}"
        return json.loads(content)

    async def complete_text(self, *, system: str, user: str) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.7,
        )
        return (resp.choices[0].message.content or "").strip()


def test_openai_key(api_key: str) -> None:
    """Makes a real, minimal completion call to verify the key works.
    Raises HTTPException(400, <provider's real error>) on failure."""
    client = OpenAI(api_key=api_key)
    try:
        client.chat.completions.create(
            model=get_settings().openai_model,
            messages=[{"role": "user", "content": "Reply with the word OK."}],
            max_tokens=5,
        )
    except AuthenticationError as exc:
        raise HTTPException(status_code=400, detail=f"OpenAI rejected the key: {exc}") from exc
    except APIError as exc:
        raise HTTPException(status_code=400, detail=f"OpenAI API error: {exc}") from exc


def get_provider(db: Session) -> LLMProvider:
    cfg = get_config(db, "openai")
    if cfg is None:
        raise HTTPException(
            status_code=409,
            detail="OpenAI is not configured yet. Complete /setup first.",
        )
    return OpenAIProvider(api_key=cfg["api_key"], model=get_settings().openai_model)
