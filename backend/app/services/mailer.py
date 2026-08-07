"""SMTP sending via the stdlib -- no extra dependency needed for sending a
plain-text-plus-HTML email, which is all this app requires."""
import smtplib
from email.headerregistry import Address
from email.message import EmailMessage
from email.utils import parseaddr

from fastapi import HTTPException


def _from_header(from_address: str, from_name: str | None) -> str:
    """Renders a display-name From header ("Jane from Acme <jane@acme.com>")
    when a name is given, else the bare address as before."""
    if not from_name:
        return from_address
    # from_address is a plain email string (validated as EmailStr at the
    # config layer); split it into local/domain for email.headerregistry.
    _, addr = parseaddr(from_address)
    local, _, domain = addr.partition("@")
    if not local or not domain:
        return from_address
    return str(Address(display_name=from_name, username=local, domain=domain))


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
    html_body: str | None = None,
    from_name: str | None = None,
) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = _from_header(from_address, from_name)
    msg["To"] = to_address
    msg.set_content(body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")

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
    html_body: str | None = None,
    from_name: str | None = None,
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
        html_body=html_body,
        from_name=from_name,
    )
