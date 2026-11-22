import os
import resend
import logging
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

#Email sending service using Resend API
def send_contact_email(submission):
    try:
        resend.api_key = os.getenv('RESEND_API_KEY')

        if not resend.api_key:
            logger.warning("RESEND_API_KEY not configured. Skipping email.")
            return False

        #Rendering HTML from Django template
        html_body = render_to_string('emails/contact_notification.html', {
            'submission': submission,
        })

        response = resend.Emails.send({
            "from": os.getenv('FROM_EMAIL', 'Jane Doe <noreply@example.org>'),
            "to": os.getenv('OWNER_EMAIL', 'user@example.com'),
            "reply_to": submission.email,
            "subject": f"New Contact Message from {submission.name}",
            "html": html_body,
        })

        logger.info(f"Contact email sent. Resend ID: {response['id']}")
        return True

    except Exception as e:
        logger.error(f"Email sending failed: {e}")
        return False