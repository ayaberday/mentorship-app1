from django.core.mail import send_mail
from django.conf import settings

def send_notification_email(subject, message, recipient_list):
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        recipient_list,
        fail_silently=False,
    )

# Exemple d'utilisation :
# send_notification_email(
#     subject="Invitation à un programme de mentoring",
#     message="Vous avez été invité à rejoindre le programme...",
#     recipient_list=["destinataire@email.com"]
# )
