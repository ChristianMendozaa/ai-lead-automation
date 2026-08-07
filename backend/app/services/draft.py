"""Draft a personalized outreach email for a lead.

Returns structured content (greeting/paragraphs/CTA/signoff), not markup --
app/services/email_render.py is solely responsible for turning this into
HTML and plain text. Keeping the model out of markup means the rendered
email always survives real mail clients, regardless of what the model
returns.
"""
from app.llm import LLMProvider
from app.models import Lead

DRAFT_SYSTEM_PROMPT = (
    "You write short, personalized, friendly B2B outreach emails on behalf "
    "of a business development rep reaching out to a new lead who submitted "
    "a contact form. Keep it concise (under 150 words total), warm, and "
    "specific to what you know about them -- avoid generic sales language. "
    "\n\n"
    "Language: write the ENTIRE reply -- subject, preheader, greeting, every "
    "paragraph, the CTA label, and the sign-off -- in the same language the "
    "lead used. Infer it from the message they submitted; if they didn't "
    "submit a message, infer it from their company website summary; if "
    "neither gives a signal, use the fallback language given in the "
    "context. Report the language you wrote in as an ISO 639-1 code (e.g. "
    '"en", "es", "fr").'
    "\n\n"
    'Respond ONLY with a JSON object of the exact shape: {"language": '
    'string, "subject": string, "preheader": string, "greeting": string, '
    '"paragraphs": array of strings, "cta_label": string, "signoff": '
    "string}. `preheader` is a one-sentence teaser (under 100 characters) "
    "shown next to the subject line in inboxes. `paragraphs` is an array of "
    "1-3 plain-text paragraphs -- no markdown, no HTML, no greeting or "
    "sign-off inside them (those go in their own fields). `greeting` should "
    "use the lead's actual first name, never a placeholder like \"[Name]\". "
    "`cta_label` should invite the specific next step given in the context "
    "(e.g. book a call), translated into the reply's language; leave it as "
    'an empty string "" if no call-to-action URL is given in the context. '
    "`signoff` should be a short closing phrase (e.g. \"Best,\") in the "
    "reply's language -- do NOT include the sender's name in it, that's "
    "appended separately. Never use a placeholder like \"[Your Name]\" "
    "anywhere."
)


def _first_name(full_name: str) -> str:
    return full_name.strip().split(" ")[0] if full_name.strip() else "there"


async def draft_email(provider: LLMProvider, lead: Lead, *, business: dict, branding: dict) -> dict:
    enrichment = lead.enrichment or {}
    context_lines = [
        f"Sender name to sign off as: {business.get('sender_name') or business.get('company_name', '')}",
        f"Sender's company: {business.get('company_name', '')}",
        f"Fallback language if the lead gives no signal (ISO 639-1): {business.get('default_language', 'en')}",
        f"Lead name: {lead.name}",
        f"Lead first name to use in greeting: {_first_name(lead.name)}",
        f"Lead email: {lead.email}",
        f"Company: {lead.company or 'unknown'}",
    ]
    if lead.raw_payload and lead.raw_payload.get("message"):
        context_lines.append(f"Message they submitted: {lead.raw_payload['message']}")
    if enrichment.get("available"):
        context_lines += [
            f"Industry: {enrichment.get('industry', '')}",
            f"What they sell: {enrichment.get('what_they_sell', '')}",
            f"Size hints: {enrichment.get('size_hints', '')}",
            f"Notable: {enrichment.get('notable', '')}",
        ]
        if enrichment.get("language"):
            context_lines.append(f"Language of their website: {enrichment['language']}")
    else:
        context_lines.append("No company website enrichment is available.")

    if branding.get("brand_tone"):
        context_lines.append(f"Brand tone to match: {branding['brand_tone']}")
    if branding.get("industry"):
        context_lines.append(f"Sender's industry: {branding['industry']}")
    if branding.get("description"):
        context_lines.append(f"About the sender's business: {branding['description']}")
    if branding.get("value_proposition"):
        context_lines.append(f"Value proposition to weave in: {branding['value_proposition']}")
    if branding.get("cta_url"):
        context_lines.append(
            "Call-to-action to invite them to (write cta_label for this, "
            f"translated into the reply's language): {branding.get('cta_label') or 'Book a call'}"
        )
    else:
        context_lines.append("No call-to-action URL is configured -- leave cta_label empty.")

    result = await provider.complete_json(
        system=DRAFT_SYSTEM_PROMPT,
        user="\n".join(context_lines),
    )

    paragraphs = result.get("paragraphs")
    if not isinstance(paragraphs, list) or not paragraphs:
        # Back-compat: an older prompt/model returning the legacy flat
        # {"subject", "body"} shape instead of structured paragraphs.
        legacy_body = result.get("body", "")
        paragraphs = [p.strip() for p in str(legacy_body).strip().split("\n\n") if p.strip()]

    return {
        "language": (result.get("language") or business.get("default_language") or "en").strip()[:8],
        "subject": str(result.get("subject", "")).strip(),
        "preheader": str(result.get("preheader", "")).strip(),
        "greeting": str(result.get("greeting", "")).strip(),
        "paragraphs": [str(p).strip() for p in paragraphs if str(p).strip()],
        "cta_label": str(result.get("cta_label", "")).strip(),
        "signoff": str(result.get("signoff", "")).strip(),
    }
