import csv
from django.core.management.base import BaseCommand
from accounts.models import FeedbackForm, FeedbackResponse, FeedbackAnswer

class Command(BaseCommand):
    help = "Exporte les réponses aux formulaires de feedback au format CSV."

    def add_arguments(self, parser):
        parser.add_argument('--form_id', type=int, help='ID du formulaire de feedback à exporter')

    def handle(self, *args, **options):
        form_id = options.get('form_id')
        if not form_id:
            self.stdout.write(self.style.ERROR('Veuillez fournir un --form_id'))
            return
        try:
            form = FeedbackForm.objects.get(id=form_id)
        except FeedbackForm.DoesNotExist:
            self.stdout.write(self.style.ERROR('Formulaire non trouvé'))
            return
        filename = f'feedback_export_form_{form_id}.csv'
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Utilisateur', 'Date', 'Question', 'Réponse'])
            for response in form.responses.all():
                for answer in response.answers.all():
                    writer.writerow([
                        response.user.username,
                        response.date_reponse,
                        answer.question.texte,
                        answer.answer
                    ])
        self.stdout.write(self.style.SUCCESS(f'Export terminé : {filename}'))
