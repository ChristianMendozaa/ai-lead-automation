from app.services.slack import _with_query_param


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
