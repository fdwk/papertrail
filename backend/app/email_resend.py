"""Transactional email via Resend (password reset, etc.)."""
from __future__ import annotations

import logging
import os
from html import escape
from urllib.parse import quote

import resend

logger = logging.getLogger("backend")

_DEFAULT_FROM = "Papertrail <no-reply@send.papertrail.wiki>"
_RESET_SUBJECT = "Reset your Papertrail password"


def _api_key() -> str:
    return os.getenv("RESEND_API_KEY", "").strip()


def public_web_app_url() -> str:
    return (
        os.getenv("PUBLIC_WEB_APP_URL", "").strip()
        or os.getenv("FRONTEND_URL", "").strip()
        or "http://localhost:3000"
    ).rstrip("/")


def reset_password_email_from() -> str:
    return os.getenv("RESEND_FROM", _DEFAULT_FROM).strip() or _DEFAULT_FROM


def build_reset_password_url(raw_token: str) -> str:
    safe_tok = quote(raw_token, safe="")
    return f"{public_web_app_url()}/reset-password?token={safe_tok}"


def _reset_email_html(reset_url: str) -> str:
    safe_url = escape(reset_url, quote=True)
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background-color:#f4f4f5;font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:#f4f4f5;padding:24px 16px;">
<tr><td align="center">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:600px;background-color:#ffffff;border:1px solid #e4e4e7;">
<tr><td style="padding:32px 28px;">
<p style="margin:0 0 8px 0;font-size:14px;line-height:1.5;color:#71717a;">Papertrail</p>
<h1 style="margin:0 0 16px 0;font-size:22px;line-height:1.3;color:#18181b;font-weight:700;">Reset your password</h1>
<p style="margin:0 0 20px 0;font-size:16px;line-height:1.6;color:#3f3f46;">We received a request to reset the password for your account. Use the button below to choose a new password.</p>
<table role="presentation" cellspacing="0" cellpadding="0" style="margin:0 0 24px 0;">
<tr><td style="border-radius:2px;background-color:#18181b;">
<a href="{safe_url}" style="display:inline-block;padding:14px 28px;font-size:16px;font-weight:600;color:#ffffff;text-decoration:none;">Reset password</a>
</td></tr></table>
<p style="margin:0 0 12px 0;font-size:14px;line-height:1.6;color:#3f3f46;">If the button does not work, copy and paste this link into your browser:</p>
<p style="margin:0 0 24px 0;font-size:14px;line-height:1.5;word-break:break-all;"><a href="{safe_url}" style="color:#2563eb;">{safe_url}</a></p>
<p style="margin:0 0 8px 0;font-size:14px;line-height:1.6;color:#52525b;">This link expires in <strong>one hour</strong>.</p>
<p style="margin:0;font-size:14px;line-height:1.6;color:#52525b;">If you did not request a password reset, you can ignore this email. Your password will stay the same.</p>
</td></tr></table>
<p style="margin:16px 0 0 0;font-size:12px;line-height:1.5;color:#a1a1aa;text-align:center;">This message was sent by Papertrail.</p>
</td></tr></table>
</body></html>\
"""


def _reset_email_text(reset_url: str) -> str:
    return f"""\
Reset your Papertrail password

We received a request to reset the password for your account. Open the link below to choose a new password (expires in one hour):

{reset_url}

If you did not request this, you can ignore this email.
"""


def send_password_reset_email(to_email: str, reset_url: str) -> None:
    """
    Send password reset message. Raises on Resend/transport errors so callers can log.
    """
    key = _api_key()
    if not key:
        raise RuntimeError("RESEND_API_KEY is not set")
    resend.api_key = key
    params: resend.Emails.SendParams = {
        "from": reset_password_email_from(),
        "to": [to_email],
        "subject": _RESET_SUBJECT,
        "html": _reset_email_html(reset_url),
        "text": _reset_email_text(reset_url),
    }
    resend.Emails.send(params)
