"""
Email sending via Resend.
Falls back to console-print mode if no RESEND_API_KEY is configured.
"""

import os
from typing import Optional

RESEND_KEY = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "PainSignal <onboarding@resend.dev>")

# Try to use resend if available
try:
    import resend
    if RESEND_KEY:
        resend.api_key = RESEND_KEY
        RESEND_READY = True
    else:
        RESEND_READY = False
except ImportError:
    RESEND_READY = False


def send_email(to_email: str, subject: str, html_body: str) -> bool:
    """Send an email. Returns True on success."""

    if not RESEND_READY:
        # Dev mode — just print to console
        print(f"\n[EMAIL — DEV MODE — would have sent to {to_email}]")
        print(f"  Subject: {subject}")
        print(f"  Body (first 200 chars): {html_body[:200]}...\n")
        return True

    try:
        params = {
            "from": FROM_EMAIL,
            "to": [to_email],
            "subject": subject,
            "html": html_body
        }
        result = resend.Emails.send(params)
        print(f"[EMAIL] Sent to {to_email}: {result}")
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False


# ─── Email Templates ──────────────────────────────────────────────

WELCOME_EMAIL_HTML = """
<div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 600px; margin: 0 auto; background: #0a0a0f; color: #f4f4f5; padding: 40px;">
  <h1 style="background: linear-gradient(135deg, #a78bfa, #38bdf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 32px; margin-bottom: 24px;">
    Welcome to PainSignal 🎯
  </h1>
  <p style="font-size: 16px; line-height: 1.6; color: #d4d4d8;">
    Hey founder,
  </p>
  <p style="font-size: 16px; line-height: 1.6; color: #d4d4d8;">
    You're on the list. We'll send you a fresh intelligence report every Monday with the highest-opportunity pain points we've detected across Reddit, Hacker News, and review sites.
  </p>
  <p style="font-size: 16px; line-height: 1.6; color: #d4d4d8;">
    <strong style="color: #a78bfa;">First report drops this Monday.</strong>
  </p>
  <div style="margin: 32px 0; padding: 24px; background: rgba(167,139,250,0.08); border-radius: 12px; border: 1px solid rgba(167,139,250,0.2);">
    <p style="margin: 0; color: #c4b5fd; font-size: 14px;">
      <strong>This week's top finding:</strong><br/>
      Small business owners are getting "ghosted by basically everyone" — sudden unexplained slowdowns. Opportunity score: 8.24/10.
    </p>
  </div>
  <p style="font-size: 14px; color: #71717a; margin-top: 32px;">
    Want the full live dashboard with all 86 pain points? <a href="http://localhost:8000/dashboard.html" style="color: #a78bfa;">Upgrade to Builder →</a>
  </p>
  <p style="font-size: 12px; color: #52525b; margin-top: 48px; border-top: 1px solid #27272a; padding-top: 16px;">
    PainSignal · You can unsubscribe anytime.
  </p>
</div>
"""


def send_welcome_email(to_email: str) -> bool:
    return send_email(
        to_email=to_email,
        subject="Welcome to PainSignal — your first report is coming",
        html_body=WELCOME_EMAIL_HTML
    )


def send_payment_confirmation(to_email: str, plan: str) -> bool:
    html = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto; background: #0a0a0f; color: #f4f4f5; padding: 40px;">
      <h1 style="color: #10b981;">You're in. Welcome to {plan.title()} 🚀</h1>
      <p style="color: #d4d4d8;">Your subscription is active. You now have full access to the PainSignal dashboard.</p>
      <a href="http://localhost:8000/dashboard.html" style="display: inline-block; padding: 12px 24px; background: linear-gradient(135deg, #a78bfa, #38bdf8); color: white; text-decoration: none; border-radius: 8px; font-weight: 600;">Open Dashboard →</a>
    </div>
    """
    return send_email(to_email, f"Welcome to PainSignal {plan.title()}", html)
