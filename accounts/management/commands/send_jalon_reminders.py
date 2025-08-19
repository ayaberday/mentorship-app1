from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import Jalon, Binome
from accounts.utils import send_notification_email
from datetime import timedelta

class Command(BaseCommand):
    help = "Envoie un rappel par email une semaine avant la date d'échéance d'un jalon."

    def handle(self, *args, **options):
        today = timezone.now().date()
        target_date = today + timedelta(days=7)
        jalons = Jalon.objects.filter(date_echeance=target_date)
        for jalon in jalons:
            binomes = Binome.objects.filter(programme=jalon.programme)
            for binome in binomes:
                mentor_email = binome.mentor.email
                mentore_email = binome.mentore.email
                subject = f"Rappel : Jalon '{jalon.titre}' à venir dans le programme '{jalon.programme.nom}'"
                message = f"Le jalon '{jalon.titre}' est prévu pour le {jalon.date_echeance}. Merci de préparer vos actions."
                send_notification_email(subject, message, [mentor_email, mentore_email])
        self.stdout.write(self.style.SUCCESS('Rappels envoyés pour les jalons à J-7.'))
