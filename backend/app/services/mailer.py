"""SMTP sending via the stdlib -- no extra dependency needed for plain
send-an-email, which is all this app requires."""
import smtplib
from email.message import EmailMessage

from fastapi import HTTPException


def _send(
    *,
    host: str,
    port: int,
    username: str,
    password: str,
    from_address: str,
    to_address: str,
    subject: str,
    body: str,
) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_address
    msg["To"] = to_address
    msg.set_content(body)

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=15) as server:
                server.login(username, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=15) as server:
                server.starttls()
                server.login(username, password)
                server.send_message(msg)
    except (smtplib.SMTPException, OSError) as exc:
        raise HTTPException(status_code=400, detail=f"SMTP error: {exc}") from exc


def send_test_email(
    *, host: str, port: int, username: str, password: str, from_address: str, test_recipient: str
) -> None:
    _send(
        host=host,
        port=port,
        username=username,
        password=password,
        from_address=from_address,
        to_address=test_recipient,
        subject="AI Lead Automation: SMTP test",
        body="This is a test email confirming your SMTP credentials work.",
    )


def send_outreach_email(
    *,
    host: str,
    port: int,
    username: str,
    password: str,
    from_address: str,
    to_address: str,
    subject: str,
    body: str,
) -> None:
    _send(
        host=host,
        port=port,
        username=username,
        password=password,
        from_address=from_address,
        to_address=to_address,
        subject=subject,
        body=body,
    )
