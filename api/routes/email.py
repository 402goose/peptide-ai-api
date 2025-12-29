"""
Peptide AI - Email Endpoints

Endpoints for sending emails to users.
"""

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional

router = APIRouter()

# Initialize Resend if API key is available
resend_client = None
try:
    import resend
    api_key = os.getenv("RESEND_API_KEY")
    if api_key:
        resend.api_key = api_key
        resend_client = resend
except ImportError:
    pass


class SendJourneyEmailRequest(BaseModel):
    """Request to email a journey plan"""
    to_email: EmailStr
    journey_title: str
    journey_content: str  # Pre-formatted text content


class SendEmailResponse(BaseModel):
    """Response from sending an email"""
    success: bool
    message: str
    email_id: Optional[str] = None


@router.post("/email/journey", response_model=SendEmailResponse)
async def send_journey_email(body: SendJourneyEmailRequest):
    """
    Send a journey plan to the user's email.

    The journey content should be pre-formatted by the frontend.
    """
    if not resend_client:
        raise HTTPException(
            status_code=503,
            detail="Email service not configured. Please set RESEND_API_KEY."
        )

    try:
        # Send the email
        result = resend_client.Emails.send({
            "from": "Peptide AI <noreply@peptide.ai>",
            "to": [body.to_email],
            "subject": f"Your Journey Plan: {body.journey_title}",
            "text": body.journey_content,
            "html": _format_journey_html(body.journey_title, body.journey_content),
        })

        return SendEmailResponse(
            success=True,
            message="Email sent successfully",
            email_id=result.get("id") if isinstance(result, dict) else str(result)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send email: {str(e)}"
        )


def _format_journey_html(title: str, content: str) -> str:
    """Convert plain text journey content to simple HTML email"""
    # Escape HTML characters
    import html
    escaped_content = html.escape(content)

    # Convert line breaks to <br> and preserve formatting
    html_content = escaped_content.replace('\n', '<br>\n')

    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #3b82f6, #6366f1); padding: 20px; border-radius: 12px 12px 0 0;">
        <h1 style="color: white; margin: 0; font-size: 24px;">Your Peptide Journey</h1>
        <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0 0;">{html.escape(title)}</p>
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
