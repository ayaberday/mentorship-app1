from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Binome
from .models import JalonBinome
from .utils import send_notification_email

@receiver(post_save, sender=Binome)
def send_invitation_emails(sender, instance, created, **kwargs):
    if created:
        mentor_email = instance.mentor.email
        mentore_email = instance.mentore.email
        programme_nom = instance.programme.nom
        subject = f"Invitation au programme de mentoring : {programme_nom}"
        message_mentor = f"Bonjour {instance.mentor.username},\n\nVous avez été assigné comme mentor dans le programme '{programme_nom}'."
        message_mentore = f"Bonjour {instance.mentore.username},\n\nVous avez été assigné comme mentoré dans le programme '{programme_nom}'."
        send_notification_email(subject, message_mentor, [mentor_email])
        send_notification_email(subject, message_mentore, [mentore_email])


# Notification lors du changement de statut d'un jalon pour un binôme
@receiver(post_save, sender=JalonBinome)
def notify_jalon_status(sender, instance, **kwargs):
    mentor_email = instance.binome.mentor.email
    mentore_email = instance.binome.mentore.email
    jalon_titre = instance.jalon.titre
    programme_nom = instance.binome.programme.nom
    if instance.statut == 'WAIT':
        # Le mentoré a marqué le jalon comme réalisé
        subject = f"Validation requise : Jalon '{jalon_titre}' dans le programme '{programme_nom}'"
        message = f"Bonjour {instance.binome.mentor.username},\n\nLe mentoré {instance.binome.mentore.username} a marqué le jalon '{jalon_titre}' comme réalisé. Merci de le valider."
        send_notification_email(subject, message, [mentor_email])
    elif instance.statut == 'DONE':
        # Le mentor a validé le jalon
        subject = f"Jalon '{jalon_titre}' validé dans le programme '{programme_nom}'"
        message = f"Le jalon '{jalon_titre}' a été validé par le mentor {instance.binome.mentor.username}. Félicitations !"
        send_notification_email(subject, message, [mentor_email, mentore_email])

        # Notification pour remplir le formulaire de feedback si associé au jalon
        feedback_forms = instance.jalon.feedback_forms.all()
        for form in feedback_forms:
            feedback_subject = f"Feedback à remplir : {form.titre} ({jalon_titre})"
            feedback_message = f"Merci de remplir le formulaire de feedback '{form.titre}' pour le jalon '{jalon_titre}'."
            send_notification_email(feedback_subject, feedback_message, [mentor_email, mentore_email])
