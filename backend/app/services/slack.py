"""Slack notifications via plain HTTPS calls to the Slack Web API -- no SDK
dependency needed for the two calls this app makes.

Approval uses plain URL buttons (not Slack's interactive block actions),
since the buttons link to the app's own /approval page. That sidesteps
needing Slack "Interactivity" (a public Request URL) configured at all --
one less manual setup step for the user. /approval resumes n8n's
per-execution wait webhook server-side, so the approver's browser never
sees n8n's raw JSON response or needs a route to n8n at all.
"""
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from fastapi import HTTPException

SLACK_API = "https://slack.com/api"


def _with_query_param(url: str, key: str, value: str) -> str:
    """Adds a query param to a URL that may already have one -- n8n's
    $execution.resumeUrl always includes `?signature=...`, so naively
    appending `?key=value` produces a malformed double-`?` URL that fails
    n8n's signature check."""
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    query[key] = value
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def build_approval_link(app_base_url: str, resume_url: str, decision: str, *, lead_name: str) -> str:
    """Builds the URL a Slack button links to: the app's own /approval page,
    carrying the *already-decided* n8n resume URL (with `decision` merged
    in via `_with_query_param`) as a query param. The page resolves the
    decision from that embedded resume URL, never from an outer param, so
    there's no way for the displayed decision to diverge from the one n8n
    acts on. `lead_name` is display-only, for the confirmation page's copy.
    """
    resume = _with_query_param(resume_url, "decision", decision)
    query = urlencode({"resume": resume, "lead": lead_name})
    return f"{app_base_url.rstrip('/')}/approval?{query}"


async def _post(token: str, method: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{SLACK_API}/{method}",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
    data = resp.json()
    if not data.get("ok"):
        raise HTTPException(
            status_code=400, detail=f"Slack API error ({method}): {data.get('error')}"
        )
    return data


async def send_test_message(bot_token: str, channel: str) -> None:
    await _post(
        bot_token,
        "chat.postMessage",
        {
            "channel": channel,
            "text": "✅ AI Lead Automation is connected to this channel.",
        },
    )


async def send_approval_request(
    bot_token: str,
    channel: str,
    *,
    app_base_url: str,
    lead_name: str,
    lead_email: str,
    company: str | None,
    subject: str,
    body: str,
    resume_url: str,
) -> str | None:
    approve_url = build_approval_link(app_base_url, resume_url, "approve", lead_name=lead_name)
    reject_url = build_approval_link(app_base_url, resume_url, "reject", lead_name=lead_name)

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*New outreach draft ready for approval*\n"
                    f"*Lead:* {lead_name} <{lead_email}>"
                    + (f" ({company})" if company else "")
                ),
            },
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Subject:* {subject}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": body},
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "✅ Approve & Send"},
                    "style": "primary",
                    "url": approve_url,
                    "action_id": "approve",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "❌ Reject"},
                    "style": "danger",
                    "url": reject_url,
                    "action_id": "reject",
                },
            ],
        },
    ]

    data = await _post(
        bot_token,
        "chat.postMessage",
        {
            "channel": channel,
            "text": f"New outreach draft ready for approval: {subject}",
            "blocks": blocks,
        },
    )
    return data.get("ts")
