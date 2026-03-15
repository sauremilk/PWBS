"""Transaktions-Email-Service (TASK-176).

Zentraler Email-Service mit konfigurierbarem Backend (SMTP oder SendGrid).
Jinja2-basierte HTML-Templates fuer Willkommens-Mail, Passwort-Reset und
System-Benachrichtigungen. DSGVO-konform: kein Tracking, Abmelde-Link
und Impressum in jeder Email.

Konfiguration ueber Umgebungsvariablen:
  EMAIL_PROVIDER: "smtp" (default) | "sendgrid"
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_USE_TLS
  SENDGRID_API_KEY
  EMAIL_FROM_ADDRESS, EMAIL_FROM_NAME
  EMAIL_UNSUBSCRIBE_URL, EMAIL_IMPRESSUM_URL
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Protocol

import aiosmtplib
import httpx
import jinja2

from pwbs.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "email"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EmailMessage:
    """Represents a single outbound email."""

    to: str
    subject: str
    html_body: str
    from_address: str
    from_name: str
    unsubscribe_url: str = ""


@dataclass(frozen=True, slots=True)
class EmailResult:
    """Result of an email send attempt."""

    success: bool
    message_id: str | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Email backend protocol
# ---------------------------------------------------------------------------


class EmailBackend(Protocol):
    """Protocol for swappable email transport backends."""

    async def send(self, message: EmailMessage) -> EmailResult: ...


# ---------------------------------------------------------------------------
# SMTP backend
# ---------------------------------------------------------------------------


class SmtpBackend:
    """Sends emails via SMTP using aiosmtplib."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        use_tls: bool,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._use_tls = use_tls

    async def send(self, message: EmailMessage) -> EmailResult:
        mime = MIMEMultipart("alternative")
        mime["From"] = f"{message.from_name} <{message.from_address}>"
        mime["To"] = message.to
        mime["Subject"] = message.subject
        mime["List-Unsubscribe"] = f"<{message.unsubscribe_url}>"
        mime.attach(MIMEText(message.html_body, "html", "utf-8"))

        try:
            response, msg = await aiosmtplib.send(
                mime,
                hostname=self._host,
                port=self._port,
                username=self._username or None,
                password=self._password or None,
                start_tls=self._use_tls,
            )
            logger.info(
                "SMTP email sent: to=%s subject=%s response=%s",
                message.to,
                message.subject,
                response,
            )
            return EmailResult(success=True, message_id=msg)
        except aiosmtplib.SMTPException as exc:
            logger.error(
                "SMTP send failed: to=%s error=%s",
                message.to,
                str(exc),
            )
            return EmailResult(success=False, error=str(exc))

# ---------------------------------------------------------------------------
# SendGrid backend (HTTP API, no SDK dependency)
# ---------------------------------------------------------------------------


class SendGridBackend:
    """Sends emails via SendGrid v3 API using httpx."""

    _API_URL = "https://api.sendgrid.com/v3/mail/send"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def send(self, message: EmailMessage) -> EmailResult:
        payload: dict[str, Any] = {
            "personalizations": [{"to": [{"email": message.to}]}],
            "from": {
                "email": message.from_address,
                "name": message.from_name,
            },
            "subject": message.subject,
            "content": [{"type": "text/html", "value": message.html_body}],
        }
        if message.unsubscribe_url:
            payload["headers"] = {
                "List-Unsubscribe": f"<{message.unsubscribe_url}>",
            }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    self._API_URL, json=payload, headers=headers
                )
                resp.raise_for_status()

            msg_id = resp.headers.get("X-Message-Id", "")
            logger.info(
                "SendGrid email sent: to=%s subject=%s message_id=%s",
                message.to,
                message.subject,
                msg_id,
            )
            return EmailResult(success=True, message_id=msg_id)
        except httpx.HTTPStatusError as exc:
            error_msg = f"SendGrid HTTP {exc.response.status_code}: {exc.response.text}"
            logger.error(
                "SendGrid send failed: to=%s error=%s",
                message.to,
                error_msg,
            )
            return EmailResult(success=False, error=error_msg)
        except httpx.RequestError as exc:
            logger.error(
                "SendGrid network error: to=%s error=%s",
                message.to,
                str(exc),
            )
            return EmailResult(success=False, error=str(exc))

# ---------------------------------------------------------------------------
# Email Service (template rendering + dispatch)
# ---------------------------------------------------------------------------


class EmailService:
    """Central email service with Jinja2 template rendering.

    Renders HTML templates from ``pwbs/templates/email/`` and dispatches
    via the configured backend (SMTP or SendGrid).
    """

    def __init__(
        self,
        backend: EmailBackend,
        settings: Settings | None = None,
        *,
        template_dir: Path | None = None,
    ) -> None:
        self._backend = backend
        self._settings = settings or get_settings()
        tpl_dir = template_dir or _TEMPLATE_DIR
        self._jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(tpl_dir)),
            autoescape=jinja2.select_autoescape(["html"]),
            undefined=jinja2.StrictUndefined,
        )

    def _render(self, template_name: str, context: dict[str, Any]) -> str:
        """Render an email template with base context variables."""
        base_context = {
            "unsubscribe_url": self._settings.email_unsubscribe_url,
            "impressum_url": self._settings.email_impressum_url,
        }
        base_context.update(context)
        tpl = self._jinja_env.get_template(template_name)
        return tpl.render(**base_context)

    async def _send(
        self, to: str, subject: str, template: str, context: dict[str, Any]
    ) -> EmailResult:
        html_body = self._render(template, {**context, "subject": subject})
        msg = EmailMessage(
            to=to,
            subject=subject,
            html_body=html_body,
            from_address=self._settings.email_from_address,
            from_name=self._settings.email_from_name,
            unsubscribe_url=self._settings.email_unsubscribe_url,
        )
        return await self._backend.send(msg)

    # -- Public API ----------------------------------------------------------

    async def send_welcome(
        self,
        to: str,
        display_name: str,
        dashboard_url: str = "http://localhost:3000/dashboard",
    ) -> EmailResult:
        """Send welcome email after registration."""
        return await self._send(
            to=to,
            subject="Willkommen bei PWBS",
            template="welcome.html",
            context={
                "display_name": display_name,
                "dashboard_url": dashboard_url,
            },
        )

    async def send_password_reset(
        self,
        to: str,
        reset_url: str,
        expires_in_minutes: int = 30,
    ) -> EmailResult:
        """Send password reset email."""
        return await self._send(
            to=to,
            subject="PWBS - Passwort zuruecksetzen",
            template="password_reset.html",
            context={
                "reset_url": reset_url,
                "expires_in_minutes": expires_in_minutes,
            },
        )

    async def send_briefing_notification(
        self,
        to: str,
        briefing_type: str,
        briefing_title: str,
        briefing_url: str,
        briefing_summary: str = "",
    ) -> EmailResult:
        """Send notification that a new briefing is ready."""
        return await self._send(
            to=to,
            subject=f"PWBS - Neues {briefing_type}",
            template="briefing_notification.html",
            context={
                "briefing_type": briefing_type,
                "briefing_title": briefing_title,
                "briefing_url": briefing_url,
                "briefing_summary": briefing_summary,
            },
        )

    async def send_briefing_email(
        self,
        to: str,
        briefing_type: str,
        briefing_title: str,
        briefing_content: str,
        briefing_url: str,
        sources: list[dict[str, str]] | None = None,
    ) -> EmailResult:
        """Send the full briefing content as an HTML email (TASK-177).

        Parameters
        ----------
        sources:
            List of dicts with keys ``title``, optional ``url``, optional ``source_type``.
        """
        return await self._send(
            to=to,
            subject=f"PWBS - {briefing_title}",
            template="briefing_email.html",
            context={
                "briefing_type": briefing_type,
                "briefing_title": briefing_title,
                "briefing_content": briefing_content,
                "briefing_url": briefing_url,
                "sources": sources or [],
            },
        )

    async def send_export_ready(
        self,
        to: str,
        export_id: str,
    ) -> EmailResult:
        """Send notification that a DSGVO data export is ready (TASK-202)."""
        return await self._send(
            to=to,
            subject="PWBS - Ihr Datenexport ist bereit",
            template="export_ready.html",
            context={
                "export_id": export_id,
            },
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_email_service(
    settings: Settings | None = None,
    *,
    backend: EmailBackend | None = None,
    template_dir: Path | None = None,
) -> EmailService:
    """Create an EmailService with the backend configured via Settings.

    Parameters
    ----------
    settings:
        Application settings. Uses ``get_settings()`` if not provided.
    backend:
        Override the backend (useful for testing).
    template_dir:
        Override the template directory (useful for testing).
    """
    s = settings or get_settings()

    if backend is None:
        if s.email_provider == "sendgrid":
            api_key = s.sendgrid_api_key.get_secret_value()
            if not api_key:
                raise ValueError(
                    "SENDGRID_API_KEY must be set when email_provider='sendgrid'"
                )
            backend = SendGridBackend(api_key=api_key)
        else:
            backend = SmtpBackend(
                host=s.smtp_host,
                port=s.smtp_port,
                username=s.smtp_user,
                password=s.smtp_password.get_secret_value(),
                use_tls=s.smtp_use_tls,
            )

    return EmailService(backend, s, template_dir=template_dir)
