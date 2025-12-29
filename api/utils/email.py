"""
Peptide AI - Email Utilities

Shared email sending functionality using Gmail SMTP.
"""

import os
import smtplib
import ssl
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Tuple
import html

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def get_smtp_credentials() -> Optional[Tuple[str, str]]:
    """Get SMTP credentials from environment"""
    user = os.getenv("GMAIL_USER")
    password = os.getenv("GMAIL_APP_PASSWORD")
    if user and password:
        logger.info(f"SMTP credentials found for {user}")
        return user, password
    logger.warning(f"SMTP credentials missing - GMAIL_USER: {'set' if user else 'missing'}, GMAIL_APP_PASSWORD: {'set' if password else 'missing'}")
    return None


def send_email(
    to_email: str,
    subject: str,
    text_content: str,
    html_content: Optional[str] = None
) -> bool:
    """
    Send an email via Gmail SMTP.

    Returns True if successful, False otherwise.
    """
    credentials = get_smtp_credentials()
    if not credentials:
        logger.error(f"Cannot send email to {to_email} - no SMTP credentials")
        return False

    gmail_user, gmail_password = credentials

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"Peptide AI <{gmail_user}>"
        msg["To"] = to_email

        # Attach plain text
        msg.attach(MIMEText(text_content, "plain"))

        # Attach HTML if provided
        if html_content:
            msg.attach(MIMEText(html_content, "html"))

        # Send via Gmail SMTP
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, to_email, msg.as_string())

        logger.info(f"Email sent successfully to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


def format_feedback_update_email(
    update_title: str,
    update_message: str,
    original_feedback_summary: str,
    test_instructions: Optional[str] = None
) -> Tuple[str, str]:
    """
    Format an email for feedback update notification.

    Returns (text_content, html_content)
    """
    # Plain text version
    text_parts = [
        f"Great news! We've made updates based on your feedback.",
        f"",
        f"YOUR ORIGINAL FEEDBACK:",
        f"{original_feedback_summary}",
        f"",
        f"WHAT WE CHANGED:",
        f"{update_message}",
    ]

    if test_instructions:
        text_parts.extend([
            f"",
            f"HOW TO TEST:",
            f"{test_instructions}",
        ])

    text_parts.extend([
        f"",
        f"Thank you for helping us improve Peptide AI!",
        f"",
        f"- The Peptide AI Team",
    ])

    text_content = "\n".join(text_parts)

    # HTML version
    escaped_title = html.escape(update_title)
    escaped_message = html.escape(update_message).replace('\n', '<br>')
    escaped_summary = html.escape(original_feedback_summary).replace('\n', '<br>')
    escaped_instructions = html.escape(test_instructions or "").replace('\n', '<br>') if test_instructions else ""

    test_section = ""
    if test_instructions:
        test_section = f"""
        <div style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 8px; padding: 16px; margin-top: 16px;">
            <h3 style="color: #166534; margin: 0 0 8px 0; font-size: 14px;">How to Test</h3>
            <p style="margin: 0; color: #15803d; font-size: 14px;">{escaped_instructions}</p>
        </div>
        """

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escaped_title}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #10b981, #059669); padding: 20px; border-radius: 12px 12px 0 0;">
        <h1 style="color: white; margin: 0; font-size: 24px;">Your Feedback Made a Difference!</h1>
        <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0 0;">{escaped_title}</p>
    </div>

    <div style="background: #f8fafc; padding: 24px; border: 1px solid #e2e8f0; border-top: none; border-radius: 0 0 12px 12px;">
        <div style="background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 16px;">
            <h3 style="color: #64748b; margin: 0 0 8px 0; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px;">Your Original Feedback</h3>
            <p style="margin: 0; color: #475569; font-size: 14px; font-style: italic;">{escaped_summary}</p>
        </div>

        <div style="background: #eff6ff; border: 1px solid #93c5fd; border-radius: 8px; padding: 16px;">
            <h3 style="color: #1d4ed8; margin: 0 0 8px 0; font-size: 14px;">What We Changed</h3>
            <p style="margin: 0; color: #1e40af; font-size: 14px;">{escaped_message}</p>
        </div>

        {test_section}
    </div>

    <div style="text-align: center; padding: 20px; color: #64748b; font-size: 12px;">
        <p style="margin: 0;">Thank you for helping us improve!</p>
        <p style="margin: 8px 0 0 0;"><a href="https://peptide.ai" style="color: #3b82f6;">Peptide AI</a> - Your personal peptide research assistant</p>
    </div>
</body>
</html>
"""

    return text_content, html_content
