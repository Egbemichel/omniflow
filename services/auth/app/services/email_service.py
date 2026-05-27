import os
import resend

resend.api_key = os.getenv("RESEND_API_KEY")

FROM_EMAIL = os.getenv("MAGIC_LINK_FROM_EMAIL", "onboarding@resend.dev")


def send_magic_link(to_email: str, magic_link: str):
    resend.Emails.send(
        {
            "from": FROM_EMAIL,
            "to": to_email,
            "subject": "Your OmniFlow Sign-in Link",
            "html": f"""
            <h2>Sign in to OmniFlow</h2>
            <p>Click the link below to sign in.
            This link expires in 15 minutes and can only be used once.</p>
            <a href="{magic_link}" style="
                display: inline-block;
                padding: 12px 24px;
                background: #0066cc;
                color: white;
                text-decoration: none;
                border-radius: 6px;
                font-weight: bold;
            ">Sign in to OmniFlow</a>
            <p>If you didn't request this, you can safely ignore this email.</p>
        """,
        }
    )
