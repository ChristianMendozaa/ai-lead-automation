"""Slack notifications via plain HTTPS calls to the Slack Web API -- no SDK
dependency needed for the two calls this app makes.

Approval uses plain URL buttons (not Slack's interactive block actions),
since the buttons link straight to n8n's per-execution resume URL. That
sidesteps needing Slack "Interactivity" (a public Request URL) configured
at all -- one less manual setup step for the user.
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
    lead_name: str,
    lead_email: str,
    company: str | None,
    subject: str,
    body: str,
    resume_url: str,
) -> str | None:
    approve_url = _with_query_param(resume_url, "decision", "approve")
    reject_url = _with_query_param(resume_url, "decision", "reject")

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
