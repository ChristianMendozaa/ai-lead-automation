"""Renders the LLM's structured draft content into a branded, email-safe
HTML message plus a matching plain-text fallback.

This is the only module in the app that knows about HTML markup -- the LLM
(app/services/draft.py) never emits HTML, it returns structured content
(greeting, paragraphs, CTA label, ...). Keeping rendering deterministic and
template-based (rather than model-generated) means the output always
survives Outlook/Gmail's clipped CSS support and never needs sanitizing
against whatever the model felt like emitting.

Pure functions only -- no DB, no network -- so this is unit-testable the
same way the rest of app/services is.
"""
import html
from urllib.parse import urlsplit

# Neutral palette matching frontend/app/globals.css, used whenever a business
# hasn't filled in (or hasn't reached) the optional branding step yet.
DEFAULT_BRANDING: dict = {
    "primary_color": "#0f172a",
    "accent_color": "#2563eb",
    "background_color": "#f8fafc",
    "text_color": "#0f172a",
    "logo_url": "",
    "font_family": "sans",
    "brand_tone": "professional",
    "industry": "",
    "description": "",
    "value_proposition": "",
    "cta_label": "",
    "cta_url": "",
    "sender_title": "",
    "sender_phone": "",
    "website_url": "",
    "tagline": "",
    "address": "",
    "social_links": [],
    "unsubscribe_line": "",
}

# Email-safe font stacks only -- webfonts don't load in most mail clients.
FONT_STACKS: dict = {
    "sans": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
    "serif": "Georgia, 'Times New Roman', Times, serif",
    "mono": "'SF Mono', Consolas, 'Liberation Mono', Menlo, monospace",
    "rounded": "'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif",
}

# Sample content for the /setup branding preview -- never sent to a lead.
SAMPLE_CONTENT: dict = {
    "language": "en",
    "subject": "Great to connect, Alex",
    "preheader": "A quick note about how we can help your team.",
    "greeting": "Hi Alex,",
    "paragraphs": [
        "Thanks for reaching out through our site -- it's great to hear from "
        "you. Based on what you shared, I think there's a strong fit between "
        "what you're building and what we do.",
        "I'd love to find 20 minutes to learn more about your goals and show "
        "you how we've helped similar teams get started quickly.",
    ],
    "cta_label": "Book a call",
    "signoff": "Best,",
}


def _safe_url(url: str | None) -> str:
    """Returns url unchanged if it's http(s), else "" -- blocks javascript:
    and other dangerous schemes from logo/CTA/social links."""
    if not url:
        return ""
    url = url.strip()
    try:
        scheme = urlsplit(url).scheme.lower()
    except ValueError:
        return ""
    if scheme not in ("http", "https"):
        return ""
    return url


def resolve_branding(cfg: dict | None) -> dict:
    """Merges a stored branding config dict over the neutral defaults, so a
    partially-filled or entirely absent `branding` config key still renders
    a complete, valid branding dict. Never subscript branding directly --
    always go through this first."""
    merged = dict(DEFAULT_BRANDING)
    if cfg:
        for key, default in DEFAULT_BRANDING.items():
            value = cfg.get(key, default)
            merged[key] = value if value not in (None, "") else default
    merged["logo_url"] = _safe_url(merged.get("logo_url"))
    merged["cta_url"] = _safe_url(merged.get("cta_url"))
    merged["website_url"] = _safe_url(merged.get("website_url"))
    social_links = merged.get("social_links") or []
    merged["social_links"] = [
        {"label": link.get("label", ""), "url": _safe_url(link.get("url"))}
        for link in social_links
        if isinstance(link, dict) and _safe_url(link.get("url"))
    ]
    return merged


def _paragraphs(content: dict) -> list[str]:
    paragraphs = content.get("paragraphs")
    if isinstance(paragraphs, list) and paragraphs:
        return [str(p) for p in paragraphs if str(p).strip()]
    # Back-compat: an older/legacy caller or a model that ignored the schema
    # and returned a flat "body" string instead of "paragraphs".
    body = content.get("body")
    if isinstance(body, str) and body.strip():
        return [p.strip() for p in body.strip().split("\n\n") if p.strip()]
    return []


def render_text(content: dict, *, branding: dict, business: dict) -> str:
    """Deterministic plain-text fallback. This is what's stored in
    lead.draft_body and posted to Slack for approval -- unaffected by any
    HTML changes."""
    lines: list[str] = []
    greeting = content.get("greeting", "").strip()
    if greeting:
        lines += [greeting, ""]

    lines += _paragraphs(content)

    cta_label = content.get("cta_label", "").strip()
    cta_url = branding.get("cta_url", "")
    if cta_label and cta_url:
        lines += ["", f"{cta_label}: {cta_url}"]

    signoff = content.get("signoff", "").strip()
    sender_name = business.get("sender_name") or business.get("company_name", "")
    signature_lines = [signoff] if signoff else []
    if sender_name:
        signature_lines.append(sender_name)
    if branding.get("sender_title"):
        signature_lines.append(branding["sender_title"])
    if business.get("company_name") and business.get("company_name") != sender_name:
        signature_lines.append(business["company_name"])
    if branding.get("sender_phone"):
        signature_lines.append(branding["sender_phone"])
    if branding.get("website_url"):
        signature_lines.append(branding["website_url"])

    if signature_lines:
        lines += [""] + signature_lines

    return "\n".join(lines).strip() + "\n"


def _button_html(label: str, url: str, *, accent_color: str) -> str:
    # "Bulletproof" table-based button -- renders consistently across
    # Outlook (which ignores padding/border-radius on <a>) and modern
    # webmail clients alike.
    return f"""
      <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin: 24px 0;">
        <tr>
          <td align="center" bgcolor="{html.escape(accent_color)}" style="border-radius: 6px;">
            <a href="{html.escape(url)}" target="_blank"
               style="display: inline-block; padding: 12px 24px; font-size: 15px;
                      font-weight: 600; color: #ffffff; text-decoration: none;
                      border-radius: 6px;">
              {html.escape(label)}
            </a>
          </td>
        </tr>
      </table>
    """


def render_html(content: dict, *, branding: dict, business: dict) -> str:
    """Renders a 600px, table-based, fully inline-CSS HTML email. No
    <style> block and no flex/grid -- Outlook's Word rendering engine
    ignores both."""
    language = html.escape(content.get("language") or "en")
    subject = html.escape(content.get("subject", ""))
    preheader = html.escape(content.get("preheader", ""))
    greeting = html.escape(content.get("greeting", ""))
    signoff = html.escape(content.get("signoff", ""))

    font_stack = FONT_STACKS.get(branding.get("font_family", "sans"), FONT_STACKS["sans"])
    primary = html.escape(branding.get("primary_color") or DEFAULT_BRANDING["primary_color"])
    accent = html.escape(branding.get("accent_color") or DEFAULT_BRANDING["accent_color"])
    background = html.escape(branding.get("background_color") or DEFAULT_BRANDING["background_color"])
    text_color = html.escape(branding.get("text_color") or DEFAULT_BRANDING["text_color"])

    company_name = html.escape(business.get("company_name", ""))
    sender_name = html.escape(business.get("sender_name") or business.get("company_name", ""))

    logo_url = branding.get("logo_url", "")
    if logo_url:
        header_html = (
            f'<img src="{html.escape(logo_url)}" alt="{company_name}" '
            f'height="32" style="height: 32px; max-width: 220px; display: block;">'
        )
    else:
        header_html = (
            f'<span style="font-size: 18px; font-weight: 700; color: {primary};">'
            f"{company_name}</span>"
        )

    paragraphs_html = "".join(
        f'<p style="margin: 0 0 16px 0; font-size: 15px; line-height: 1.6; color: {text_color};">'
        f"{html.escape(p)}</p>"
        for p in _paragraphs(content)
    )

    cta_label = content.get("cta_label", "").strip()
    cta_url = branding.get("cta_url", "")
    cta_html = _button_html(cta_label, cta_url, accent_color=accent) if (cta_label and cta_url) else ""

    signature_lines = [sender_name]
    if branding.get("sender_title"):
        signature_lines.append(html.escape(branding["sender_title"]))
    if company_name and company_name != sender_name:
        signature_lines.append(company_name)
    if branding.get("sender_phone"):
        signature_lines.append(html.escape(branding["sender_phone"]))
    signature_html = "<br>".join(line for line in signature_lines if line)

    footer_bits = []
    if branding.get("tagline"):
        footer_bits.append(html.escape(branding["tagline"]))
    if branding.get("address"):
        footer_bits.append(html.escape(branding["address"]))
    social_links = branding.get("social_links") or []
    if social_links:
        footer_bits.append(
            " &middot; ".join(
                f'<a href="{html.escape(link["url"])}" style="color: {text_color};">'
                f'{html.escape(link["label"] or link["url"])}</a>'
                for link in social_links
            )
        )
    if branding.get("unsubscribe_line"):
        footer_bits.append(html.escape(branding["unsubscribe_line"]))
    footer_html = "<br>".join(footer_bits)

    return f"""<!doctype html>
<html lang="{language}">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
  </head>
  <body style="margin: 0; padding: 0; background: {background}; font-family: {font_stack};">
    <span style="display: none; max-height: 0; overflow: hidden; opacity: 0;">{preheader}</span>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"
           style="background: {background};">
      <tr>
        <td align="center" style="padding: 32px 16px;">
          <table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0"
                 style="max-width: 600px; width: 100%; background: #ffffff; border-radius: 8px; overflow: hidden;">
            <tr>
              <td style="padding: 24px 32px; border-bottom: 1px solid #e2e8f0;">
                {header_html}
              </td>
            </tr>
            <tr>
              <td style="padding: 32px;">
                {f'<p style="margin: 0 0 16px 0; font-size: 15px; color: {text_color};">{greeting}</p>' if greeting else ""}
                {paragraphs_html}
                {cta_html}
                {f'<p style="margin: 24px 0 0 0; font-size: 15px; color: {text_color};">{signoff}<br>{signature_html}</p>' if (signoff or signature_html) else ""}
              </td>
            </tr>
            <tr>
              <td style="padding: 20px 32px; background: #f8fafc; font-size: 12px; line-height: 1.6; color: #64748b;">
                {footer_html}
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""
