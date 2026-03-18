"""Email service — sends transactional emails via Resend. No-op if no API key configured."""

from __future__ import annotations

import asyncio
from typing import Literal

import structlog

from syndicate.config import settings

logger = structlog.get_logger()


def send_email(to: str, subject: str, html: str) -> bool:
    """Send an email via Resend. Returns True on success, False otherwise. No-op if no API key."""
    if not settings.resend_api_key:
        logger.debug("email_skipped_no_key", to=to, subject=subject)
        return False

    try:
        import resend

        resend.api_key = settings.resend_api_key
        resend.Emails.send(
            {
                "from": settings.email_from,
                "to": [to],
                "subject": subject,
                "html": html,
            }
        )
        logger.info("email_sent", to=to, subject=subject)
        return True
    except Exception as e:
        logger.error("email_send_failed", to=to, subject=subject, error=str(e))
        return False


def _base_html(title: str, body: str) -> str:
    """Dark-themed email wrapper matching the Syndicate UI."""
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#09090b;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<div style="max-width:560px;margin:0 auto;padding:40px 24px;">
  <div style="margin-bottom:32px;">
    <span style="font-size:20px;font-weight:700;color:#fff;letter-spacing:-0.02em;">SYNDICATE</span>
    <span style="font-size:14px;color:#71717a;margin-left:4px;">.ai</span>
  </div>
  <div style="background:#18181b;border:1px solid #27272a;border-radius:12px;padding:32px;">
    <h1 style="margin:0 0 16px;font-size:20px;font-weight:700;color:#fff;">{title}</h1>
    {body}
  </div>
  <p style="margin-top:24px;font-size:11px;color:#52525b;text-align:center;">
    Syndicate.ai — Autonomous AI Hedge Fund
  </p>
</div>
</body>
</html>"""


def send_welcome_email(
    email: str,
    display_name: str,
    bearer_token: str,
    agents_created: int,
    estimated_cost: float,
) -> bool:
    """Send welcome email after registration."""
    body = f"""
    <p style="color:#a1a1aa;font-size:14px;line-height:1.6;margin:0 0 20px;">
      Welcome to Syndicate, <strong style="color:#fff;">{display_name}</strong>. Your agents are being deployed.
    </p>
    <div style="background:#09090b;border:1px solid #27272a;border-radius:8px;padding:16px;margin-bottom:20px;">
      <p style="margin:0 0 8px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.15em;color:#71717a;">
        Bearer Token (backup)
      </p>
      <code style="display:block;font-size:12px;color:#8b5cf6;word-break:break-all;font-family:'SF Mono',Monaco,monospace;">
        {bearer_token}
      </code>
    </div>
    <div style="display:flex;gap:12px;margin-bottom:20px;">
      <div style="flex:1;background:#09090b;border:1px solid #27272a;border-radius:8px;padding:12px;text-align:center;">
        <p style="margin:0;font-size:10px;color:#71717a;text-transform:uppercase;letter-spacing:0.1em;">Agents</p>
        <p style="margin:4px 0 0;font-size:24px;font-weight:700;color:#fff;">{agents_created}</p>
      </div>
      <div style="flex:1;background:#09090b;border:1px solid #27272a;border-radius:8px;padding:12px;text-align:center;">
        <p style="margin:0;font-size:10px;color:#71717a;text-transform:uppercase;letter-spacing:0.1em;">Est. Cost/mo</p>
        <p style="margin:4px 0 0;font-size:24px;font-weight:700;color:#fff;">${estimated_cost:.2f}</p>
      </div>
    </div>
    <p style="color:#a1a1aa;font-size:13px;line-height:1.6;margin:0 0 20px;">
      <strong style="color:#fff;">Next steps:</strong> The Board of Directors will assign your agents to teams.
      They start in quarantine and earn full voting weight after 20 signals.
    </p>
    <a href="https://syndicatefund.ai/profile"
       style="display:block;text-align:center;background:#8b5cf6;color:#fff;padding:12px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px;">
      View Your Profile
    </a>"""
    return send_email(email, "Welcome to Syndicate — Your Agents Are Live", _base_html("Welcome to Syndicate", body))


def send_status_change_email(
    email: str,
    display_name: str,
    action: Literal["paused", "resumed", "cancelled"],
) -> bool:
    """Send notification email when contributor status changes."""
    messages = {
        "paused": {
            "title": "Contribution Paused",
            "desc": "Your agents have been paused and will not participate in the next pipeline cycle. You can resume at any time from your profile.",
            "color": "#f59e0b",
        },
        "resumed": {
            "title": "Contribution Resumed",
            "desc": "Your agents are back online and will participate in the next pipeline cycle.",
            "color": "#22c55e",
        },
        "cancelled": {
            "title": "Contribution Cancelled",
            "desc": "Your contribution has been cancelled. All agents have been fired and API keys have been wiped. Thank you for contributing to Syndicate.",
            "color": "#ef4444",
        },
    }
    msg = messages[action]
    body = f"""
    <p style="color:#a1a1aa;font-size:14px;line-height:1.6;margin:0 0 20px;">
      Hi <strong style="color:#fff;">{display_name}</strong>,
    </p>
    <div style="border-left:3px solid {msg['color']};padding-left:16px;margin-bottom:20px;">
      <p style="color:#fff;font-size:15px;font-weight:600;margin:0 0 8px;">{msg['title']}</p>
      <p style="color:#a1a1aa;font-size:13px;line-height:1.6;margin:0;">{msg['desc']}</p>
    </div>
    <a href="https://syndicatefund.ai/profile"
       style="display:inline-block;background:#27272a;color:#fff;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:500;font-size:13px;">
      View Profile
    </a>"""
    return send_email(email, f"Syndicate — {msg['title']}", _base_html(msg["title"], body))


def fire_and_forget_email(coro_or_fn, *args) -> None:
    """Schedule an email send as a fire-and-forget background task."""
    try:
        loop = asyncio.get_running_loop()

        async def _send():
            try:
                await asyncio.to_thread(coro_or_fn, *args)
            except Exception as e:
                logger.error("fire_and_forget_email_failed", error=str(e), fn=getattr(coro_or_fn, "__name__", "?"))

        loop.create_task(_send())
    except RuntimeError:
        pass  # No event loop — skip (e.g., testing)
