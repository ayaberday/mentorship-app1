from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)

def send_notification_email(subject, message, recipient_list):
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        recipient_list,
        fail_silently=False,
    )

class EmailNotificationService:
    """Service centralisé pour toutes les notifications email de l'application"""
    
    @staticmethod
    def send_html_email(subject, template_name, context, recipient_list):
        """Envoie un email avec template HTML et version texte"""
        try:
            # Rendu des templates
            html_content = render_to_string(f'emails/{template_name}.html', context)
            text_content = render_to_string(f'emails/{template_name}.txt', context)
            
            # Création de l'email multipart
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=recipient_list
            )
            email.attach_alternative(html_content, "text/html")
            
            # Envoi
            email.send()
            logger.info(f"Email envoyé avec succès: {subject} à {recipient_list}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'email: {str(e)}")
            return False
    
    @staticmethod
    def notify_jalon_realise(jalon, mentor, mentore):
        """Notifie le mentor qu'un jalon a été marqué comme réalisé"""
        context = {
            'jalon': jalon,
            'mentor': mentor,
            'mentore': mentore,
            'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000'
        }
        
        return EmailNotificationService.send_html_email(
            subject=f"Jalon réalisé: {jalon.titre}",
            template_name='jalon_realise',
            context=context,
            recipient_list=[mentor.email]
        )
    
    @staticmethod
    def notify_jalon_valide(jalon, mentor, mentore):
        """Notifie le mentoré qu'un jalon a été validé"""
        context = {
            'jalon': jalon,
            'mentor': mentor,
            'mentore': mentore,
            'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000'
        }
        
        return EmailNotificationService.send_html_email(
            subject=f"Jalon validé: {jalon.titre}",
            template_name='jalon_valide',
            context=context,
            recipient_list=[mentore.email]
        )
    
    @staticmethod
    def notify_nouveau_feedback(feedback_form, recipient_list):
        """Notifie les utilisateurs d'un nouveau formulaire de feedback"""
        context = {
            'feedback_form': feedback_form,
            'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000'
        }
        
        return EmailNotificationService.send_html_email(
            subject=f"Nouveau formulaire de feedback: {feedback_form.title}",
            template_name='nouveau_feedback',
            context=context,
            recipient_list=recipient_list
        )
    
    @staticmethod
    def send_jalon_reminder(jalon, user, days_until_due):
        """Envoie un rappel pour un jalon à venir"""
        context = {
            'jalon': jalon,
            'user': user,
            'days_until_due': days_until_due,
            'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000'
        }
        
        if days_until_due > 0:
            subject = f"Rappel: Jalon à venir dans {days_until_due} jour(s)"
        else:
            subject = f"Urgent: Jalon en retard de {abs(days_until_due)} jour(s)"
        
        return EmailNotificationService.send_html_email(
            subject=subject,
            template_name='jalon_upcoming',
            context=context,
            recipient_list=[user.email]
        )

# Exemple d'utilisation :
# send_notification_email(
#     subject="Invitation à un programme de mentoring",
#     message="Vous avez été invité à rejoindre le programme...",
#     recipient_list=["destinataire@email.com"]
# )
