import pytest
from fastapi import HTTPException

from app.services.normalize import (
    derive_website_url,
    normalize_company,
    normalize_email,
    normalize_phone,
)


def test_normalize_email_lowercases_and_trims():
    assert normalize_email("  Jane.Doe@ExAmple.COM ") == "jane.doe@example.com"


def test_normalize_email_rejects_garbage():
    with pytest.raises(HTTPException) as exc_info:
        normalize_email("not-an-email")
    assert exc_info.value.status_code == 422


def test_normalize_phone_strips_formatting():
    assert normalize_phone("(555) 123-4567 ext.") == "5551234567"


def test_normalize_phone_keeps_leading_plus():
    assert normalize_phone("+1 555-123-4567") == "+15551234567"


def test_normalize_phone_none_passthrough():
    assert normalize_phone(None) is None
    assert normalize_phone("   ") is None


def test_normalize_company_collapses_whitespace():
    assert normalize_company("  Acme   Corp \n") == "Acme Corp"


@pytest.mark.parametrize(
    "email,expected",
    [
        ("person@gmail.com", None),
        ("person@yahoo.com", None),
        ("person@icloud.com", None),
        ("jane@acmecorp.io", "https://acmecorp.io"),
        ("jane@sub.acmecorp.com", "https://sub.acmecorp.com"),
    ],
)
def test_derive_website_url(email, expected):
    assert derive_website_url(email) == expected
