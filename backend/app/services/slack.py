"""Slack notifications via plain HTTPS calls to the Slack Web API -- no SDK
dependency needed for the two calls this app makes.

Approval uses plain URL buttons (not Slack's interactive block actions),
since the buttons link straight to n8n's per-execution resume URL. That
sidesteps needing Slack "Interactivity" (a public Request URL) configured
at all -- one less manual setup step for the user.
"""
import httpx
from fastapi import HTTPException

SLACK_API = "https://slack.com/api"


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
            "text": "✅ Leads Automation is connected to this channel.",
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
    approve_url = f"{resume_url}?decision=approve"
    reject_url = f"{resume_url}?decision=reject"

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
