"""Extract structured signal about a lead's company from scraped HTML."""
import re

from bs4 import BeautifulSoup

from app.llm import LLMProvider

MAX_TEXT_CHARS = 15_000

ENRICH_SYSTEM_PROMPT = (
    "You analyze a company's website text and extract a short structured "
    "summary for a sales rep who is about to email them. Respond ONLY with "
    'a JSON object of the exact shape: {"industry": string, '
    '"what_they_sell": string, "size_hints": string, "notable": string}. '
    "Each value should be a brief phrase or short sentence. If the text "
    'gives no signal for a field, use an empty string "".'
)


def html_to_text(html: str) -> str:
    if not html or not html.strip():
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(" ")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:MAX_TEXT_CHARS]


async def enrich_from_html(provider: LLMProvider, scraped_html: str) -> dict:
    text = html_to_text(scraped_html)
    if not text:
        return {"available": False}

    result = await provider.complete_json(
        system=ENRICH_SYSTEM_PROMPT,
        user=f"Website text:\n\n{text}",
    )
    result["available"] = True
    return result
