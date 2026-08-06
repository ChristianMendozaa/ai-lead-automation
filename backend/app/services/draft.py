"""Draft a personalized outreach email subject + body for a lead."""
from app.llm import LLMProvider
from app.models import Lead

DRAFT_SYSTEM_PROMPT = (
    "You write short, personalized, friendly B2B outreach emails on behalf "
    "of a business development rep reaching out to a new lead who submitted "
    "a contact form. Keep it concise (under 150 words), warm, and specific "
    "to what you know about them -- avoid generic sales language. Respond "
    'ONLY with a JSON object of the exact shape: {"subject": string, '
    '"body": string}. The body should be plain text (no markdown), ready '
    "to send as-is, and should NOT include a greeting placeholder like "
    '"[Name]" -- use their actual first name. Sign off using the sender '
    "name and company given in the context -- never use a placeholder "
    'like "[Your Name]".'
)


def _first_name(full_name: str) -> str:
    return full_name.strip().split(" ")[0] if full_name.strip() else "there"


async def draft_email(
    provider: LLMProvider, lead: Lead, *, sender_name: str, company_name: str
) -> dict:
    enrichment = lead.enrichment or {}
    context_lines = [
        f"Sender name to sign off as: {sender_name}",
        f"Sender's company: {company_name}",
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
    else:
        context_lines.append("No company website enrichment is available.")

    result = await provider.complete_json(
        system=DRAFT_SYSTEM_PROMPT,
        user="\n".join(context_lines),
    )
    return {
        "subject": result.get("subject", "").strip(),
        "body": result.get("body", "").strip(),
    }
