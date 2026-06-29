import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime


# ── Config — pull from environment variables, never hardcode ─────────────────
SMTP_HOST     = os.environ.get("SMTP_HOST",     "smtp.gmail.com")
SMTP_PORT     = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER     = os.environ.get("SMTP_USER",     "")   # your Gmail address
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")   # Gmail App Password


def send_bill_email(
    recipient_email: str,
    customer_name:   str,
    total_bill:      int,
    pdf_path:        str,
) -> dict:
    """
    Sends a bill PDF as an email attachment.

    Returns a dict: {"success": bool, "message": str}

    Setup note:
        Gmail requires an App Password (not your regular password).
        Enable it at: myaccount.google.com → Security → App Passwords
        Then set env vars:
            export SMTP_USER="you@gmail.com"
            export SMTP_PASSWORD="your_16_char_app_password"
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        return {
            "success": False,
            "message": "SMTP credentials not configured. Set SMTP_USER and SMTP_PASSWORD env vars.",
        }

    if not os.path.exists(pdf_path):
        return {"success": False, "message": f"PDF not found at path: {pdf_path}"}

    try:
        msg = MIMEMultipart("mixed")
        msg["Subject"] = f"Your Smart Trolley Invoice — ₹{total_bill}"
        msg["From"]    = SMTP_USER
        msg["To"]      = recipient_email

        # ── Plain text fallback ────────────────────────────────────────────────
        text_body = f"""
Hi {customer_name},

Thank you for shopping with Smart Trolley!

Your total bill amount is: ₹{total_bill}
Date: {datetime.now().strftime("%d %b %Y, %I:%M %p")}

Please find your detailed invoice attached as a PDF.

— Smart Trolley Team
        """.strip()

        # ── HTML body ──────────────────────────────────────────────────────────
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body       {{ font-family: Arial, sans-serif; background: #f4f6fb; margin: 0; padding: 0; }}
    .container {{ max-width: 520px; margin: 40px auto; background: #fff;
                  border-radius: 10px; overflow: hidden;
                  box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
    .header    {{ background: #1a1a2e; color: white; padding: 30px;
                  text-align: center; }}
    .header h1 {{ margin: 0; font-size: 24px; }}
    .header p  {{ margin: 6px 0 0; font-size: 13px; opacity: 0.7; }}
    .body      {{ padding: 30px; }}
    .amount    {{ font-size: 38px; font-weight: bold; color: #1a1a2e;
                  text-align: center; margin: 20px 0; }}
    .detail    {{ color: #555; font-size: 14px; text-align: center;
                  margin-bottom: 24px; }}
    .footer    {{ background: #f4f6fb; text-align: center;
                  padding: 16px; font-size: 12px; color: #999; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Smart Trolley</h1>
      <p>Automated Retail Billing System</p>
    </div>
    <div class="body">
      <p>Hi <strong>{customer_name}</strong>,</p>
      <p>Thank you for shopping with us! Here is your invoice summary:</p>
      <div class="amount">₹{total_bill}</div>
      <div class="detail">
        Date: {datetime.now().strftime("%d %b %Y, %I:%M %p")}
      </div>
      <p>Your detailed itemised bill is attached as a PDF.</p>
    </div>
    <div class="footer">Smart Trolley &bull; Automated Retail Billing</div>
  </div>
</body>
</html>
        """.strip()

        body = MIMEMultipart("alternative")
        body.attach(MIMEText(text_body, "plain", "utf-8"))
        body.attach(MIMEText(html_body, "html", "utf-8"))
        msg.attach(body)

        # ── Attach PDF ─────────────────────────────────────────────────────────
        with open(pdf_path, "rb") as f:
            pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
            pdf_attachment.add_header(
                "Content-Disposition",
                "attachment",
                filename=os.path.basename(pdf_path),
            )
            msg.attach(pdf_attachment)

        # ── Send ───────────────────────────────────────────────────────────────
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, recipient_email, msg.as_string())

        return {"success": True, "message": f"Invoice emailed to {recipient_email}"}

    except smtplib.SMTPAuthenticationError:
        return {
            "success": False,
            "message": "SMTP authentication failed. Check your App Password.",
        }
    except Exception as e:
        return {"success": False, "message": f"Email failed: {str(e)}"}