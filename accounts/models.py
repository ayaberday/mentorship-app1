from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager

class User(AbstractUser):
    ROLE_CHOICES = [
        ('ADF', 'Super Administrateur'),
        ('RH', 'Gestionnaire RH'),
        ('MENTOR', 'Mentor'),
        ('MENTEE', 'Mentoré'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='custom_user_set',
        related_query_name='custom_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='custom_user_set',
        related_query_name='custom_user',
    )
    
    objects = UserManager()

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

# Programme de mentoring
class Programme(models.Model):
    nom = models.CharField(max_length=100)
    description = models.TextField()
    date_debut = models.DateField()
    date_fin = models.DateField()
    gestionnaire = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'RH'})

    def __str__(self):
        return self.nom

# Jalon du programme
class Jalon(models.Model):
    programme = models.ForeignKey(Programme, on_delete=models.CASCADE, related_name='jalons')
    titre = models.CharField(max_length=100)
    description = models.TextField()
    date_echeance = models.DateField()

    def __str__(self):
        return f"{self.titre} ({self.programme.nom})"

# Binôme mentor/mentoré
class Binome(models.Model):
    programme = models.ForeignKey(Programme, on_delete=models.CASCADE, related_name='binomes')
    mentor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mentors', limit_choices_to={'role': 'MENTOR'})
    mentore = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mentores', limit_choices_to={'role': 'MENTEE'})

    def __str__(self):
        return f"{self.mentor.username} / {self.mentore.username} ({self.programme.nom})"

# Formulaire de feedback
class FeedbackForm(models.Model):
    programme = models.ForeignKey(Programme, on_delete=models.CASCADE, related_name='feedback_forms')
    jalon = models.ForeignKey(Jalon, on_delete=models.CASCADE, null=True, blank=True, related_name='feedback_forms')
    titre = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titre

# Question du formulaire
class FeedbackQuestion(models.Model):
    QUESTION_TYPES = [
        ('SCALE', 'Échelle de notation'),
        ('TEXT', 'Réponse ouverte'),
        ('CHOICE', 'Choix multiple'),
    ]
    form = models.ForeignKey(FeedbackForm, on_delete=models.CASCADE, related_name='questions')
    texte = models.CharField(max_length=255)
    type = models.CharField(max_length=10, choices=QUESTION_TYPES)
    choices = models.TextField(blank=True, help_text="Séparer les choix par une virgule pour le QCM")

    def __str__(self):
        return self.texte

# Réponse au formulaire
class FeedbackResponse(models.Model):
    form = models.ForeignKey(FeedbackForm, on_delete=models.CASCADE, related_name='responses')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date_reponse = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Réponse de {self.user.username} à {self.form.titre}"

# Réponse à chaque question
class FeedbackAnswer(models.Model):
    response = models.ForeignKey(FeedbackResponse, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(FeedbackQuestion, on_delete=models.CASCADE)
    answer = models.TextField()

    def __str__(self):
        return f"{self.question.texte}: {self.answer}"

# Suivi du statut d'un jalon pour chaque binôme
class JalonBinome(models.Model):
    STATUS_CHOICES = [
        ('TODO', 'À faire'),
        ('WAIT', 'En attente de validation'),
        ('DONE', 'Complété'),
    ]
    binome = models.ForeignKey(Binome, on_delete=models.CASCADE, related_name='jalons_binome')
    jalon = models.ForeignKey(Jalon, on_delete=models.CASCADE, related_name='jalons_binome')
    statut = models.CharField(max_length=10, choices=STATUS_CHOICES, default='TODO')
    commentaire = models.TextField(blank=True)
    date_realisation = models.DateTimeField(null=True, blank=True)
    date_validation = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.binome} - {self.jalon.titre} [{self.get_statut_display()}]"
