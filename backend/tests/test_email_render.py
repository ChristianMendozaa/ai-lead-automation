from app.services.email_render import (
    DEFAULT_BRANDING,
    render_html,
    render_text,
    resolve_branding,
)

SAMPLE_CONTENT = {
    "language": "es",
    "subject": "Hola",
    "preheader": "Un mensaje breve",
    "greeting": "Hola María,",
    "paragraphs": ["Gracias por tu mensaje.", "Nos encantaría ayudarte."],
    "cta_label": "Agendar una llamada",
    "signoff": "Un saludo,",
}

BUSINESS = {"company_name": "Acme Corp", "sender_name": "Jane"}


def test_resolve_branding_none_returns_full_defaults():
    resolved = resolve_branding(None)
    assert resolved == DEFAULT_BRANDING


def test_resolve_branding_empty_dict_returns_full_defaults():
    assert resolve_branding({}) == DEFAULT_BRANDING


def test_resolve_branding_merges_partial_config_over_defaults():
    resolved = resolve_branding({"primary_color": "#ff0000"})
    assert resolved["primary_color"] == "#ff0000"
    assert resolved["accent_color"] == DEFAULT_BRANDING["accent_color"]


def test_render_html_escapes_script_tag_in_paragraph():
    content = dict(SAMPLE_CONTENT, paragraphs=["<script>alert(1)</script>"])
    branding = resolve_branding(None)
    out = render_html(content, branding=branding, business=BUSINESS)
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_render_html_drops_javascript_scheme_logo_and_cta():
    branding = resolve_branding(
        {
            "logo_url": "javascript:alert(1)",
            "cta_url": "javascript:alert(1)",
        }
    )
    assert branding["logo_url"] == ""
    assert branding["cta_url"] == ""
    out = render_html(SAMPLE_CONTENT, branding=branding, business=BUSINESS)
    assert "javascript:" not in out


def test_render_html_has_no_cta_button_without_cta_url():
    branding = resolve_branding(None)
    content = dict(SAMPLE_CONTENT, cta_label="Book a call")
    out = render_html(content, branding=branding, business=BUSINESS)
    assert "Book a call" not in out


def test_render_html_has_cta_button_with_cta_url():
    branding = resolve_branding({"cta_url": "https://cal.com/jane"})
    out = render_html(SAMPLE_CONTENT, branding=branding, business=BUSINESS)
    assert "https://cal.com/jane" in out
    assert "Agendar una llamada" in out


def test_render_html_sets_lang_attribute_from_content_language():
    branding = resolve_branding(None)
    out = render_html(SAMPLE_CONTENT, branding=branding, business=BUSINESS)
    assert '<html lang="es">' in out


def test_render_text_contains_paragraphs_signoff_and_cta():
    branding = resolve_branding({"cta_url": "https://cal.com/jane"})
    out = render_text(SAMPLE_CONTENT, branding=branding, business=BUSINESS)
    assert "Gracias por tu mensaje." in out
    assert "Nos encantaría ayudarte." in out
    assert "Un saludo," in out
    assert "https://cal.com/jane" in out
    assert "Jane" in out


def test_render_text_legacy_body_field_splits_into_paragraphs():
    content = {"greeting": "Hi,", "body": "First paragraph.\n\nSecond paragraph.", "signoff": "Best,"}
    branding = resolve_branding(None)
    out = render_text(content, branding=branding, business=BUSINESS)
    assert "First paragraph." in out
    assert "Second paragraph." in out
