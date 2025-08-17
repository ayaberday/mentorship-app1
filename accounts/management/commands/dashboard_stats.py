from django.core.management.base import BaseCommand
from accounts.models import Programme, Binome, JalonBinome

class Command(BaseCommand):
    help = "Affiche les statistiques clés du mentoring."

    def add_arguments(self, parser):
        parser.add_argument('--programme_id', type=int, help='ID du programme à analyser')

    def handle(self, *args, **options):
        programme_id = options.get('programme_id')
        if not programme_id:
            self.stdout.write(self.style.ERROR('Veuillez fournir un --programme_id'))
            return
        try:
            programme = Programme.objects.get(id=programme_id)
        except Programme.DoesNotExist:
            self.stdout.write(self.style.ERROR('Programme non trouvé'))
            return
        binomes = programme.binomes.all()
        total_binomes = binomes.count()
        jalons = programme.jalons.all()
        total_jalons = jalons.count()
        completed = 0
        late = 0
        for binome in binomes:
            for jalon in jalons:
                try:
                    jb = JalonBinome.objects.get(binome=binome, jalon=jalon)
                    if jb.statut == 'DONE':
                        completed += 1
                    elif jb.statut != 'DONE' and jalon.date_echeance < jb.date_realisation:
                        late += 1
                except JalonBinome.DoesNotExist:
                    continue
        percent_completed = (completed / (total_binomes * total_jalons) * 100) if total_binomes and total_jalons else 0
        self.stdout.write(f"Programme : {programme.nom}")
        self.stdout.write(f"Binômes : {total_binomes}")
        self.stdout.write(f"Jalons : {total_jalons}")
        self.stdout.write(f"% Jalons complétés : {percent_completed:.2f}%")
        self.stdout.write(f"Binômes en retard : {late}")
