from urllib.parse import parse_qs, urlsplit

from app.services.slack import _with_query_param, build_approval_link


def test_with_query_param_on_url_with_existing_query():
    # n8n's $execution.resumeUrl always includes ?signature=... already --
    # this must join with & instead of producing a second leading ?, which
    # n8n treats as part of the signature value and rejects.
    url = "http://localhost:5678/webhook-waiting/2?signature=abc123"
    result = _with_query_param(url, "decision", "approve")
    assert result == "http://localhost:5678/webhook-waiting/2?signature=abc123&decision=approve"


def test_with_query_param_on_url_without_existing_query():
    url = "http://localhost:5678/webhook-waiting/2"
    result = _with_query_param(url, "decision", "reject")
    assert result == "http://localhost:5678/webhook-waiting/2?decision=reject"


def test_build_approval_link_embeds_decision_inside_resume_param():
    # The outer link must carry the *already-decided* resume URL as a single
    # opaque `resume` param -- there is deliberately no top-level `decision`
    # param the /approval page could read independently, since that would
    # let the displayed decision diverge from the one n8n actually applies.
    resume_url = "http://localhost:5678/webhook-waiting/2?signature=abc123"
    link = build_approval_link(
        "http://localhost:3000", resume_url, "approve", lead_name="Jane Doe"
    )

    parsed = urlsplit(link)
    assert parsed.scheme == "http"
    assert parsed.netloc == "localhost:3000"
    assert parsed.path == "/approval"

    query = parse_qs(parsed.query)
    assert query["lead"] == ["Jane Doe"]
    assert len(query["resume"]) == 1

    # The embedded resume URL round-trips intact, signature included, with
    # decision merged into its own query string (not the outer one).
    embedded = urlsplit(query["resume"][0])
    assert embedded.scheme == "http"
    assert embedded.netloc == "localhost:5678"
    assert embedded.path == "/webhook-waiting/2"
    embedded_query = parse_qs(embedded.query)
    assert embedded_query["signature"] == ["abc123"]
    assert embedded_query["decision"] == ["approve"]


def test_build_approval_link_strips_trailing_slash_from_app_base_url():
    link = build_approval_link(
        "http://localhost:3000/",
        "http://localhost:5678/webhook-waiting/2",
        "reject",
        lead_name="Jane Doe",
    )
    assert urlsplit(link).path == "/approval"
    assert "//approval" not in link
