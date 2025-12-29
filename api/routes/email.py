"""
Peptide AI - Email Endpoints

Endpoints for sending emails to users using Gmail SMTP.
"""

import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
import html

router = APIRouter()

# Gmail SMTP configuration
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


class SendJourneyEmailRequest(BaseModel):
    """Request to email a journey plan"""
    to_email: EmailStr
    journey_title: str
    journey_content: str  # Pre-formatted text content


class SendEmailResponse(BaseModel):
    """Response from sending an email"""
    success: bool
    message: str


def _get_smtp_credentials() -> tuple[str, str] | None:
    """Get SMTP credentials from environment"""
    user = os.getenv("GMAIL_USER")
    password = os.getenv("GMAIL_APP_PASSWORD")
    if user and password:
        return user, password
    return None


def _format_journey_html(title: str, content: str) -> str:
    """Convert plain text journey content to simple HTML email"""
    escaped_title = html.escape(title)
    escaped_content = html.escape(content)

    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escaped_title}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #3b82f6, #6366f1); padding: 20px; border-radius: 12px 12px 0 0;">
        <h1 style="color: white; margin: 0; font-size: 24px;">Your Peptide Journey</h1>
        <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0 0;">{escaped_title}</p>
    </div>

    <div style="background: #f8fafc; padding: 24px; border: 1px solid #e2e8f0; border-top: none; border-radius: 0 0 12px 12px;">
        <pre style="font-family: inherit; white-space: pre-wrap; word-wrap: break-word; margin: 0; font-size: 14px;">
{escaped_content}
        </pre>
    </div>

    <div style="text-align: center; padding: 20px; color: #64748b; font-size: 12px;">
        <p style="margin: 0;">Sent from <a href="https://peptide.ai" style="color: #3b82f6;">Peptide AI</a></p>
        <p style="margin: 8px 0 0 0;">Your personal peptide research assistant</p>
    </div>
</body>
</html>
"""


@router.post("/email/journey", response_model=SendEmailResponse)
async def send_journey_email(body: SendJourneyEmailRequest):
    """
    Send a journey plan to the user's email via Gmail SMTP.

    Requires GMAIL_USER and GMAIL_APP_PASSWORD environment variables.
    """
    credentials = _get_smtp_credentials()
    if not credentials:
        raise HTTPException(
            status_code=503,
            detail="Email service not configured. Please set GMAIL_USER and GMAIL_APP_PASSWORD."
        )

    gmail_user, gmail_password = credentials

    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Your Journey Plan: {body.journey_title}"
        msg["From"] = f"Peptide AI <{gmail_user}>"
        msg["To"] = body.to_email

        # Attach plain text and HTML versions
        text_part = MIMEText(body.journey_content, "plain")
        html_part = MIMEText(
            _format_journey_html(body.journey_title, body.journey_content),
            "html"
        )

        msg.attach(text_part)
        msg.attach(html_part)

        # Send via Gmail SMTP
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, body.to_email, msg.as_string())

        return SendEmailResponse(
            success=True,
            message="Email sent successfully"
        )

    except smtplib.SMTPAuthenticationError:
        raise HTTPException(
            status_code=503,
            detail="Email authentication failed. Check GMAIL_USER and GMAIL_APP_PASSWORD."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send email: {str(e)}"
        )
