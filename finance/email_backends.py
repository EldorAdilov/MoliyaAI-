import requests
from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings

class ResendEmailBackend(BaseEmailBackend):
    """
    Railway yoki boshqa SMTP portlari yopiq bo'lgan serverlarda
    Resend HTTPS API orqali xat jo'natish uchun custom Django Email Backend.
    """
    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        
        api_key = getattr(settings, 'RESEND_API_KEY', None)
        if not api_key:
            return 0
            
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        sent_count = 0
        for message in email_messages:
            from_email = message.from_email or settings.DEFAULT_FROM_EMAIL
            
            payload = {
                "from": from_email,
                "to": message.to,
                "subject": message.subject,
                "text": message.body,
            }
            
            # HTML shablonlarini qo'llab-quvvatlash (agar bo'lsa)
            if hasattr(message, 'alternatives') and message.alternatives:
                for alt, mime in message.alternatives:
                    if mime == 'text/html':
                        payload['html'] = alt
                        break
            
            try:
                response = requests.post(
                    "https://api.resend.com/emails",
                    headers=headers,
                    json=payload,
                    timeout=10
                )
                if response.status_code in [200, 201]:
                    sent_count += 1
            except Exception:
                pass
                
        return sent_count
