from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model, logout, authenticate, login
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q, Avg
from functools import wraps
from datetime import datetime, timedelta
from .forms import CustomUserCreationForm, FeedbackFormForm, FeedbackQuestionForm
from .models import User, Programme, Binome, Jalon, JalonBinome, FeedbackForm, FeedbackQuestion, FeedbackResponse, FeedbackAnswer
from accounts.utils import EmailNotificationService
from django.conf import settings
from django.http import JsonResponse, HttpResponse
import csv
import json
from io import BytesIO
try:
    import xlsxwriter
    XLSXWRITER_AVAILABLE = True
except ImportError:
    XLSXWRITER_AVAILABLE = False
    xlsxwriter = None

User = get_user_model()

def custom_logout(request):
    """Vue logout personnalisée qui redirige toujours vers home"""
    logout(request)
    messages.success(request, "Vous avez été déconnecté avec succès.")
    return redirect('home')

def role_required(allowed_roles):
    """Decorator to restrict access based on user roles"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            # Always allow Django superusers
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            if request.user.role not in allowed_roles:
                messages.error(request, "Accès non autorisé.")
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def home(request):
    return render(request, 'home.html')

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Compte créé avec succès. Connectez-vous !")
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'signup.html', {'form': form})

def custom_login(request):
    """Vue de login personnalisée avec redirection selon le rôle"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f"Bienvenue {user.get_full_name() or user.username} !")
            
            # Redirection selon le rôle
            if user.role == 'ADF':
                return redirect('dashboard')  # Dashboard Super Admin
            elif user.role == 'RH':
                return redirect('dashboard')  # Dashboard RH
            elif user.role == 'MENTOR':
                return redirect('dashboard')  # Dashboard Mentor
            elif user.role == 'MENTEE':
                return redirect('dashboard')  # Dashboard Mentoré
            else:
                return redirect('dashboard')
        else:
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
    
    return render(request, 'login.html')

@login_required
def dashboard(request):
    user = request.user
    context = {}

    if user.role == 'ADF' or user.is_superuser:
        from django.db.models import Avg, Max, Min
        
        # Basic counts
        total_users = User.objects.count()
        total_programmes = Programme.objects.count()
        total_binomes = Binome.objects.count()
        total_rh = User.objects.filter(role='RH').count()
        
        # Advanced metrics
        active_programmes = Programme.objects.filter(
            date_fin__gte=timezone.now().date()
        ).count()
        
        # User distribution
        user_distribution = {
            'mentors': User.objects.filter(role='MENTOR').count(),
            'mentees': User.objects.filter(role='MENTEE').count(),
            'rh': total_rh,
            'admins': User.objects.filter(role='ADF').count(),
        }
        
        # Recent activity (last 30 days)
        last_month = timezone.now() - timedelta(days=30)
        recent_jalons = JalonBinome.objects.filter(
            date_realisation__gte=last_month
        ).count()
        
        context.update({
            'total_users': total_users,
            'total_programmes': total_programmes,
            'total_binomes': total_binomes,
            'total_rh': total_rh,
            'active_programmes': active_programmes,
            'user_distribution': user_distribution,
            'recent_jalons': recent_jalons,
        })
        template = 'dashboard_superadmin.html'
        
    elif user.role == 'RH':
        programmes = Programme.objects.all()
        binomes = Binome.objects.all()
        
        # Detailed jalons statistics
        jalons_stats = JalonBinome.objects.aggregate(
            en_attente=Count('id', filter=Q(statut='WAIT')),
            completes=Count('id', filter=Q(statut='DONE')),
            todo=Count('id', filter=Q(statut='TODO')),
            total=Count('id')
        )
        
        # Performance metrics
        completion_rate = 0
        if jalons_stats['total'] > 0:
            completion_rate = round((jalons_stats['completes'] / jalons_stats['total']) * 100, 1)
        
        # Programme effectiveness
        programme_stats = []
        for programme in programmes:
            prog_binomes = binomes.filter(programme=programme)
            prog_jalons = JalonBinome.objects.filter(binome__in=prog_binomes)
            prog_completion = 0
            if prog_jalons.count() > 0:
                prog_completed = prog_jalons.filter(statut='DONE').count()
                prog_completion = round((prog_completed / prog_jalons.count()) * 100, 1)
            
            programme_stats.append({
                'programme': programme,
                'binomes_count': prog_binomes.count(),
                'completion_rate': prog_completion,
                'jalons_total': prog_jalons.count(),
            })
        
        # Alerts generation
        alertes = []
        
        # Alert for overdue jalons
        overdue_jalons = JalonBinome.objects.filter(
            statut='TODO',
            jalon__date_echeance__lt=timezone.now().date()
        ).count()
        if overdue_jalons > 0:
            alertes.append({
                'type': 'warning',
                'titre': f'{overdue_jalons} jalon(s) en retard',
                'message': 'Des jalons ont dépassé leur date d\'échéance.'
            })
        
        # Alert for pending validations
        pending_validations = jalons_stats['en_attente']
        if pending_validations > 5:
            alertes.append({
                'type': 'info',
                'titre': f'{pending_validations} jalons en attente',
                'message': 'Plusieurs jalons attendent une validation de mentor.'
            })
        
        # Alert for inactive binomes
        last_month = timezone.now() - timedelta(days=30)
        inactive_binomes = binomes.exclude(
            id__in=JalonBinome.objects.filter(
                date_realisation__gte=last_month
            ).values_list('binome_id', flat=True)
        ).count()
        if inactive_binomes > 0:
            alertes.append({
                'type': 'warning',
                'titre': f'{inactive_binomes} binôme(s) inactif(s)',
                'message': 'Certains binômes n\'ont pas d\'activité récente.'
            })
        
        # Recent activities
        activites_recentes = []
        recent_completions = JalonBinome.objects.filter(
            statut='DONE',
            date_validation__isnull=False
        ).order_by('-date_validation')[:5]
        
        for jalon in recent_completions:
            activites_recentes.append({
                'titre': f'Jalon validé: {jalon.jalon.nom}',
                'date': jalon.date_validation,
                'type': 'success',
                'icon': 'check-circle'
            })
        
        context.update({
            'total_programmes': programmes.count(),
            'total_binomes': binomes.count(),
            'jalons_en_attente': jalons_stats['en_attente'],
            'taux_completion': completion_rate,
            'programme_stats': programme_stats,
            'alertes': alertes,
            'activites_recentes': activites_recentes,
            'overdue_jalons': overdue_jalons,
        })
        template = 'dashboard_rh.html'
        
    elif user.role == 'MENTOR':
        mes_binomes = Binome.objects.filter(mentor=user)
        jalons_mentor = JalonBinome.objects.filter(binome__in=mes_binomes)
        
        # Detailed statistics
        jalons_stats = jalons_mentor.aggregate(
            a_valider=Count('id', filter=Q(statut='WAIT')),
            valides=Count('id', filter=Q(statut='DONE')),
            total=Count('id')
        )
        
        # Mentee performance tracking
        mentee_progress = []
        for binome in mes_binomes:
            mentee_jalons = JalonBinome.objects.filter(binome=binome)
            total_jalons = mentee_jalons.count()
            completed_jalons = mentee_jalons.filter(statut='DONE').count()
            
            progress_rate = 0
            if total_jalons > 0:
                progress_rate = round((completed_jalons / total_jalons) * 100, 1)
            
            # Recent activity
            last_activity = mentee_jalons.filter(
                date_realisation__isnull=False
            ).order_by('-date_realisation').first()
            
            mentee_progress.append({
                'binome': binome,
                'progress_rate': progress_rate,
                'completed_jalons': completed_jalons,
                'total_jalons': total_jalons,
                'last_activity': last_activity.date_realisation if last_activity else None,
            })
        
        # Jalons requiring attention (overdue or waiting too long)
        jalons_attention = jalons_mentor.filter(
            Q(statut='WAIT', date_realisation__lt=timezone.now() - timedelta(days=3)) |
            Q(statut='TODO', jalon__date_echeance__lt=timezone.now().date())
        )[:5]
        
        # Average response time for validations
        validated_jalons = jalons_mentor.filter(
            statut='DONE',
            date_realisation__isnull=False,
            date_validation__isnull=False
        )
        
        avg_response_time = None
        if validated_jalons.exists():
            response_times = []
            for jalon in validated_jalidations:
                if jalon.date_realisation and jalon.date_validation:
                    delta = jalon.date_validation - jalon.date_realisation
                    response_times.append(delta.days)
            if response_times:
                avg_response_time = round(sum(response_times) / len(response_times), 1)
        
        context.update({
            'total_mentores': mes_binomes.count(),
            'jalons_a_valider': jalons_stats['a_valider'],
            'jalons_valides': jalons_stats['valides'],
            'feedbacks_en_attente': 0,  # TODO: Calculate when feedback system is implemented
            'mentee_progress': mentee_progress,
            'jalons_attention': jalons_attention,
            'avg_response_time': avg_response_time,
            'jalons_en_attente': jalons_mentor.filter(statut='WAIT')[:5],
        })
        template = 'dashboard.html'
        
    elif user.role == 'MENTEE':
        try:
            binome = Binome.objects.get(mentore=user)
            jalons_mentee = JalonBinome.objects.filter(binome=binome)
            
            # Detailed progress statistics
            jalons_stats = jalons_mentee.aggregate(
                completes=Count('id', filter=Q(statut='DONE')),
                en_attente=Count('id', filter=Q(statut='WAIT')),
                a_faire=Count('id', filter=Q(statut='TODO')),
                total=Count('id')
            )
            
            # Progress calculation
            total = jalons_stats['total']
            completed = jalons_stats['completes']
            taux_progression = round((completed / max(total, 1)) * 100, 1)
            
            # Timeline analysis
            prochains_jalons = jalons_mentee.filter(statut='TODO').order_by('jalon__date_echeance')[:3]
            
            # Performance metrics
            jalons_en_retard = jalons_mentee.filter(
                statut='TODO',
                jalon__date_echeance__lt=timezone.now().date()
            ).count()
            
            # Recent achievements
            recent_achievements = jalons_mentee.filter(
                statut='DONE',
                date_validation__isnull=False
            ).order_by('-date_validation')[:3]
            
            # Time to completion analysis
            completed_jalons = jalons_mentee.filter(statut='DONE')
            avg_completion_time = None
            if completed_jalons.exists():
                completion_times = []
                for jalon in completed_jalons:
                    if jalon.date_realisation and jalon.binome.date_creation:
                        # Calculate days from binome creation to jalon completion
                        delta = jalon.date_realisation.date() - jalon.binome.date_creation
                        completion_times.append(delta.days)
                if completion_times:
                    avg_completion_time = round(sum(completion_times) / len(completion_times), 1)
            
            # Streak calculation (consecutive completed jalons)
            current_streak = 0
            for jalon in jalons_mentee.order_by('jalon__date_echeance'):
                if jalon.statut == 'DONE':
                    current_streak += 1
                else:
                    break
            
            # Next milestone
            next_milestone = None
            if prochains_jalons.exists():
                next_milestone = prochains_jalons.first()
                days_until_next = (next_milestone.jalon.date_echeance - timezone.now().date()).days
                next_milestone.days_until = max(0, days_until_next)
            
            context.update({
                'binome': binome,
                'jalons_completes': jalons_stats['completes'],
                'jalons_en_attente': jalons_stats['en_attente'],
                'jalons_a_faire': jalons_stats['a_faire'],
                'total_jalons': total,
                'taux_progression': taux_progression,
                'prochains_jalons': prochains_jalons,
                'jalons_en_retard': jalons_en_retard,
                'recent_achievements': recent_achievements,
                'avg_completion_time': avg_completion_time,
                'current_streak': current_streak,
                'next_milestone': next_milestone,
            })
            
        except Binome.DoesNotExist:
            context.update({
                'binome': None,
                'jalons_completes': 0,
                'jalons_en_attente': 0,
                'jalons_a_faire': 0,
                'taux_progression': 0,
                'total_jalons': 0,
                'prochains_jalons': [],
                'jalons_en_retard': 0,
                'recent_achievements': [],
                'avg_completion_time': None,
                'current_streak': 0,
                'next_milestone': None,
            })
        template = 'dashboard.html'
    else:
        template = 'home.html'

    return render(request, template, context)

@login_required
@role_required(['MENTEE'])
def jalon_realise(request, jalonbinome_id):
    """Mark milestone as completed by mentee"""
    jb = get_object_or_404(JalonBinome, id=jalonbinome_id)
    
    if request.user != jb.binome.mentore or jb.statut != 'TODO':
        messages.error(request, "Action non autorisée.")
        return redirect('jalons_timeline')
    
    if request.method == 'POST':
        commentaire = request.POST.get('commentaire', '')
        jb.commentaire = commentaire
        jb.statut = 'WAIT'
        jb.date_realisation = timezone.now()
        jb.save()
        
        if getattr(settings, 'NOTIFICATION_SETTINGS', {}).get('SEND_JALON_NOTIFICATIONS', True):
            EmailNotificationService.send_jalon_realise_notification(jb)
        
        messages.success(request, "Jalon marqué comme réalisé. En attente de validation du mentor.")
    
    return redirect('jalons_timeline')

@login_required
@role_required(['MENTOR'])
def jalon_valide(request, jalonbinome_id):
    """Validate milestone by mentor"""
    jb = get_object_or_404(JalonBinome, id=jalonbinome_id)
    
    if request.user != jb.binome.mentor or jb.statut != 'WAIT':
        messages.error(request, "Action non autorisée.")
        return redirect('jalons_timeline')
    
    if request.method == 'POST':
        jb.statut = 'DONE'
        jb.date_validation = timezone.now()
        jb.save()
        
        if getattr(settings, 'NOTIFICATION_SETTINGS', {}).get('SEND_JALON_NOTIFICATIONS', True):
            EmailNotificationService.send_jalon_valide_notification(jb)
        
        messages.success(request, "Jalon validé.")
    
    return redirect('jalons_timeline')

@login_required
def jalons_timeline(request):
    user = request.user
    
    if user.role == 'MENTOR':
        binomes = Binome.objects.filter(mentor=user)
    elif user.role == 'MENTEE':
        binomes = Binome.objects.filter(mentore=user)
    else:
        messages.error(request, "Accès non autorisé.")
        return redirect('dashboard')
    
    if not binomes.exists():
        messages.info(request, "Aucun binôme assigné.")
        return render(request, 'jalons_timeline.html', {'jalons_binome': [], 'binome': None})
    
    binome = binomes.first()
    jalons_binome = JalonBinome.objects.filter(binome=binome).select_related('jalon').order_by('jalon__date_echeance')
    
    return render(request, 'jalons_timeline.html', {
        'jalons_binome': jalons_binome, 
        'binome': binome
    })

@login_required
def mentores_list(request):
    """List mentees for a mentor"""
    binomes = Binome.objects.filter(mentor=request.user).select_related('mentore', 'programme')
    return render(request, 'mentores_list.html', {'binomes': binomes})

@login_required
def binomes_list(request):
    """List all binomes for RH and admin users"""
    if request.user.role not in ['RH', 'ADF']:
        messages.error(request, "Accès non autorisé")
        return redirect('dashboard')
    
    binomes = Binome.objects.all().select_related('mentor', 'mentore', 'programme').order_by('-created_at')
    
    # Filtrage par programme si spécifié
    programme_id = request.GET.get('programme')
    if programme_id:
        binomes = binomes.filter(programme_id=programme_id)
    
    # Filtrage par statut si spécifié
    status = request.GET.get('status')
    if status:
        binomes = binomes.filter(status=status)
    
    programmes = Programme.objects.all()
    
    context = {
        'binomes': binomes,
        'programmes': programmes,
        'selected_programme': programme_id,
        'selected_status': status,
    }
    
    return render(request, 'binomes_list.html', context)

@login_required
def create_feedback_form(request):
    """Créer un nouveau formulaire de feedback (RH uniquement)"""
    if request.user.role != 'RH':
        messages.error(request, "Accès non autorisé.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = FeedbackFormForm(request.POST)
        if form.is_valid():
            feedback_form = form.save(commit=False)
            feedback_form.created_by = request.user
            feedback_form.save()
            messages.success(request, "Formulaire créé avec succès.")
            return redirect('edit_feedback_form', form_id=feedback_form.id)
    else:
        form = FeedbackFormForm()
    
    return render(request, 'feedback/create_form.html', {'form': form})

@login_required
def edit_feedback_form(request, form_id):
    """Éditer un formulaire de feedback et ses questions"""
    if request.user.role != 'RH':
        messages.error(request, "Accès non autorisé.")
        return redirect('dashboard')
    
    feedback_form = get_object_or_404(FeedbackForm, id=form_id)
    questions = FeedbackQuestion.objects.filter(form=feedback_form).order_by('ordre')
    
    if request.method == 'POST':
        if 'add_question' in request.POST:
            question_form = FeedbackQuestionForm(request.POST)
            if question_form.is_valid():
                question = question_form.save(commit=False)
                question.form = feedback_form
                question.ordre = questions.count() + 1
                question.save()
                messages.success(request, "Question ajoutée avec succès.")
                return redirect('edit_feedback_form', form_id=form_id)
        elif 'delete_question' in request.POST:
            question_id = request.POST.get('question_id')
            question = get_object_or_404(FeedbackQuestion, id=question_id, form=feedback_form)
            question.delete()
            messages.success(request, "Question supprimée avec succès.")
            return redirect('edit_feedback_form', form_id=form_id)
    
    question_form = FeedbackQuestionForm()
    
    context = {
        'feedback_form': feedback_form,
        'questions': questions,
        'question_form': question_form,
    }
    return render(request, 'feedback/edit_form.html', context)

@login_required
def fill_feedback_form(request, form_id):
    """Remplir un formulaire de feedback"""
    feedback_form = get_object_or_404(FeedbackForm, id=form_id)
    questions = FeedbackQuestion.objects.filter(form=feedback_form).order_by('id')
    
    # Vérifier si l'utilisateur a déjà répondu
    existing_response = FeedbackResponse.objects.filter(
        form=feedback_form, user=request.user
    ).first()
    
    if existing_response and not feedback_form.allow_multiple_responses:
        messages.info(request, "Vous avez déjà répondu à ce formulaire.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        # Créer une nouvelle réponse
        response = FeedbackResponse.objects.create(
            form=feedback_form,
            user=request.user
        )
        
        # Sauvegarder les réponses aux questions
        for question in questions:
            answer_value = request.POST.get(f'question_{question.id}')
            if answer_value:
                FeedbackAnswer.objects.create(
                    response=response,
                    question=question,
                    answer=answer_value
                )
        
        messages.success(request, "Votre réponse a été enregistrée avec succès.")
        
        # Envoyer notification email au RH
        try:
            email_service = EmailNotificationService()
            email_service.send_feedback_notification(feedback_form, request.user)
        except Exception as e:
            logger.error(f"Erreur envoi email feedback: {e}")
        
        return redirect('dashboard')
    
    context = {
        'feedback_form': feedback_form,
        'questions': questions,
    }
    return render(request, 'feedback/fill_form.html', context)

@login_required
def feedback_results(request, form_id):
    """Voir les résultats d'un formulaire de feedback (RH uniquement)"""
    if request.user.role != 'RH':
        messages.error(request, "Accès non autorisé.")
        return redirect('dashboard')
    
    feedback_form = get_object_or_404(FeedbackForm, id=form_id)
    responses = FeedbackResponse.objects.filter(form=feedback_form).select_related('user')
    questions = FeedbackQuestion.objects.filter(form=feedback_form).order_by('ordre')
    
    # Calculer les statistiques
    stats = {}
    for question in questions:
        answers = FeedbackAnswer.objects.filter(question=question)
        if question.type == 'SCALE':
            # Calculer moyenne pour les questions d'échelle
            values = [int(answer.answer) for answer in answers if answer.answer.isdigit()]
            if values:
                stats[question.id] = {
                    'type': 'scale',
                    'average': sum(values) / len(values),
                    'count': len(values),
                    'distribution': {i: values.count(i) for i in range(1, 6)}
                }
        elif question.type == 'CHOICE':
            # Compter les choix
            choices = [answer.answer for answer in answers]
            stats[question.id] = {
                'type': 'choice',
                'distribution': {choice: choices.count(choice) for choice in set(choices)},
                'count': len(choices)
            }
        else:
            # Questions texte
            stats[question.id] = {
                'type': 'text',
                'count': answers.count(),
                'responses': [answer.answer for answer in answers]
            }
    
    context = {
        'feedback_form': feedback_form,
        'responses': responses,
        'questions': questions,
        'stats': stats,
    }
    return render(request, 'feedback/results.html', context)

@login_required
@role_required(['ADF', 'RH'])
def export_data(request):
    """Interface d'export de données avec options"""
    if request.method == 'GET':
        # Afficher l'interface d'export
        context = {
            'total_users': User.objects.count(),
            'total_programmes': Programme.objects.count(),
            'total_binomes': Binome.objects.count(),
            'total_jalons': JalonBinome.objects.count(),
            'total_feedbacks': FeedbackResponse.objects.count(),
        }
        return render(request, 'admin/export_data.html', context)
    
    elif request.method == 'POST':
        # Traiter la demande d'export
        export_type = request.POST.get('export_type', 'csv')
        data_types = request.POST.getlist('data_types')
        date_from = request.POST.get('date_from')
        date_to = request.POST.get('date_to')
        
        if export_type == 'csv':
            return export_csv(request, data_types, date_from, date_to)
        elif export_type == 'excel':
            return export_excel(request, data_types, date_from, date_to)
        else:
            messages.error(request, "Format d'export non supporté")
            return redirect('export_data')

def export_csv(request, data_types, date_from=None, date_to=None):
    """Export des données en format CSV"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="mentorship_export_{datetime.now().strftime("%Y%m%d_%H%M")}.csv"'
    
    # Ajouter BOM pour Excel
    response.write('\ufeff')
    writer = csv.writer(response)
    
    # Filtres de date
    date_filter = {}
    if date_from:
        date_filter['date_joined__gte'] = date_from
    if date_to:
        date_filter['date_joined__lte'] = date_to
    
    # Export des utilisateurs
    if 'users' in data_types:
        writer.writerow(['=== UTILISATEURS ==='])
        writer.writerow([
            'ID', 'Nom d\'utilisateur', 'Prénom', 'Nom', 'Email', 'Rôle', 
            'Date d\'inscription', 'Dernière connexion', 'Actif', 'Programmes'
        ])
        
        users = User.objects.filter(**date_filter).order_by('date_joined')
        for user in users:
            # Compter les programmes pour chaque utilisateur
            if user.role == 'RH':
                programmes_count = Programme.objects.filter(gestionnaire=user).count()
            elif user.role == 'MENTOR':
                programmes_count = Binome.objects.filter(mentor=user).values('programme').distinct().count()
            elif user.role == 'MENTEE':
                programmes_count = Binome.objects.filter(mentore=user).values('programme').distinct().count()
            else:
                programmes_count = 0
            
            writer.writerow([
                user.id,
                user.username,
                user.first_name,
                user.last_name,
                user.email,
                user.get_role_display(),
                user.date_joined.strftime('%d/%m/%Y %H:%M'),
                user.last_login.strftime('%d/%m/%Y %H:%M') if user.last_login else 'Jamais',
                'Oui' if user.is_active else 'Non',
                programmes_count
            ])
        writer.writerow([])
    
    # Export des programmes
    if 'programmes' in data_types:
        writer.writerow(['=== PROGRAMMES ==='])
        writer.writerow([
            'ID', 'Nom', 'Description', 'Date début', 'Date fin', 'Gestionnaire', 
            'Nb binômes', 'Nb jalons', 'Taux completion', 'Statut'
        ])
        
        for programme in Programme.objects.all().order_by('date_debut'):
            binomes = Binome.objects.filter(programme=programme)
            jalons = JalonBinome.objects.filter(binome__in=binomes)
            
            completion_rate = 0
            if jalons.count() > 0:
                completed = jalons.filter(statut='DONE').count()
                completion_rate = round((completed / jalons.count()) * 100, 1)
            
            # Déterminer le statut
            today = datetime.now().date()
            if programme.date_fin < today:
                statut = 'Terminé'
            elif programme.date_debut <= today <= programme.date_fin:
                statut = 'En cours'
            else:
                statut = 'À venir'
            
            writer.writerow([
                programme.id,
                programme.nom,
                programme.description,
                programme.date_debut.strftime('%d/%m/%Y'),
                programme.date_fin.strftime('%d/%m/%Y'),
                programme.gestionnaire.username,
                binomes.count(),
                jalons.count(),
                f"{completion_rate}%",
                statut
            ])
        writer.writerow([])
    
    # Export des binômes
    if 'binomes' in data_types:
        writer.writerow(['=== BINÔMES ==='])
        writer.writerow([
            'ID', 'Programme', 'Mentor', 'Mentoré', 'Date création', 
            'Jalons total', 'Jalons complétés', 'Jalons en attente', 'Progression %'
        ])
        
        for binome in Binome.objects.all().select_related('programme', 'mentor', 'mentore'):
            jalons = JalonBinome.objects.filter(binome=binome)
            total_jalons = jalons.count()
            completed_jalons = jalons.filter(statut='DONE').count()
            pending_jalons = jalons.filter(statut='WAIT').count()
            
            progression = round((completed_jalons / max(total_jalons, 1)) * 100, 1)
            
            writer.writerow([
                binome.id,
                binome.programme.nom,
                binome.mentor.username,
                binome.mentore.username,
                binome.date_creation.strftime('%d/%m/%Y') if hasattr(binome, 'date_creation') else 'N/A',
                total_jalons,
                completed_jalons,
                pending_jalons,
                f"{progression}%"
            ])
        writer.writerow([])
    
    # Export des jalons
    if 'jalons' in data_types:
        writer.writerow(['=== JALONS ==='])
        writer.writerow([
            'ID', 'Programme', 'Titre', 'Description', 'Binôme', 'Mentor', 'Mentoré',
            'Statut', 'Date échéance', 'Date réalisation', 'Date validation', 
            'Temps réalisation (jours)', 'Temps validation (jours)', 'Commentaire'
        ])
        
        jalons_filter = {}
        if date_from:
            jalons_filter['jalon__date_echeance__gte'] = date_from
        if date_to:
            jalons_filter['jalon__date_echeance__lte'] = date_to
        
        for jalon_binome in JalonBinome.objects.filter(**jalons_filter).select_related(
            'jalon', 'binome', 'binome__mentor', 'binome__mentore'
        ).order_by('jalon__date_echeance'):
            
            # Calculer les temps
            temps_realisation = ''
            temps_validation = ''
            
            if jalon_binome.date_realisation:
                delta_real = jalon_binome.date_realisation.date() - jalon_binome.jalon.date_echeance
                temps_realisation = delta_real.days
            
            if jalon_binome.date_validation and jalon_binome.date_realisation:
                delta_valid = jalon_binome.date_validation - jalon_binome.date_realisation
                temps_validation = delta_valid.days
            
            writer.writerow([
                jalon_binome.id,
                jalon_binome.jalon.programme.nom,
                jalon_binome.jalon.titre,
                jalon_binome.jalon.description,
                f"{jalon_binome.binome.mentor.username} / {jalon_binome.binome.mentore.username}",
                jalon_binome.binome.mentor.username,
                jalon_binome.binome.mentore.username,
                jalon_binome.get_statut_display(),
                jalon_binome.jalon.date_echeance.strftime('%d/%m/%Y'),
                jalon_binome.date_realisation.strftime('%d/%m/%Y %H:%M') if jalon_binome.date_realisation else '',
                jalon_binome.date_validation.strftime('%d/%m/%Y %H:%M') if jalon_binome.date_validation else '',
                temps_realisation,
                temps_validation,
                jalon_binome.commentaire
            ])
        writer.writerow([])
    
    # Export des feedbacks
    if 'feedbacks' in data_types:
        writer.writerow(['=== FEEDBACKS ==='])
        writer.writerow([
            'ID', 'Formulaire', 'Programme', 'Utilisateur', 'Rôle utilisateur',
            'Date réponse', 'Nb questions', 'Questions/Réponses'
        ])
        
        for response in FeedbackResponse.objects.all().select_related(
            'form', 'user', 'form__programme'
        ).order_by('-date_reponse'):
            
            answers = FeedbackAnswer.objects.filter(response=response).select_related('question')
            qa_pairs = []
            for answer in answers:
                qa_pairs.append(f"Q: {answer.question.texte} | R: {answer.answer}")
            
            writer.writerow([
                response.id,
                response.form.titre,
                response.form.programme.nom,
                response.user.username,
                response.user.get_role_display(),
                response.date_reponse.strftime('%d/%m/%Y %H:%M'),
                answers.count(),
                ' || '.join(qa_pairs)
            ])
    
    return response

def export_excel(request, data_types, date_from=None, date_to=None):
    """Export des données en format Excel avec plusieurs feuilles"""
    if not XLSXWRITER_AVAILABLE:
        messages.error(request, "Le module xlsxwriter n'est pas installé. Utilisez l'export CSV ou installez xlsxwriter avec: pip install xlsxwriter")
        return redirect('export_data')
    
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    
    # Styles
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#4472C4',
        'font_color': 'white',
        'border': 1
    })
    
    data_format = workbook.add_format({
        'border': 1,
        'text_wrap': True
    })
    
    date_format = workbook.add_format({
        'border': 1,
        'num_format': 'dd/mm/yyyy'
    })
    
    # Filtres de date
    date_filter = {}
    if date_from:
        date_filter['date_joined__gte'] = date_from
    if date_to:
        date_filter['date_joined__lte'] = date_to
    
    # Feuille Utilisateurs
    if 'users' in data_types:
        worksheet = workbook.add_worksheet('Utilisateurs')
        headers = [
            'ID', 'Nom d\'utilisateur', 'Prénom', 'Nom', 'Email', 'Rôle',
            'Date inscription', 'Dernière connexion', 'Actif', 'Programmes'
        ]
        
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        users = User.objects.filter(**date_filter).order_by('date_joined')
        for row, user in enumerate(users, 1):
            # Compter les programmes
            if user.role == 'RH':
                programmes_count = Programme.objects.filter(gestionnaire=user).count()
            elif user.role == 'MENTOR':
                programmes_count = Binome.objects.filter(mentor=user).values('programme').distinct().count()
            elif user.role == 'MENTEE':
                programmes_count = Binome.objects.filter(mentore=user).values('programme').distinct().count()
            else:
                programmes_count = 0
            
            worksheet.write(row, 0, user.id, data_format)
            worksheet.write(row, 1, user.username, data_format)
            worksheet.write(row, 2, user.first_name, data_format)
            worksheet.write(row, 3, user.last_name, data_format)
            worksheet.write(row, 4, user.email, data_format)
            worksheet.write(row, 5, user.get_role_display(), data_format)
            worksheet.write(row, 6, user.date_joined, date_format)
            worksheet.write(row, 7, user.last_login if user.last_login else 'Jamais', data_format)
            worksheet.write(row, 8, 'Oui' if user.is_active else 'Non', data_format)
            worksheet.write(row, 9, programmes_count, data_format)
        
        # Ajuster la largeur des colonnes
        worksheet.set_column('A:A', 5)
        worksheet.set_column('B:B', 15)
        worksheet.set_column('C:D', 12)
        worksheet.set_column('E:E', 25)
        worksheet.set_column('F:F', 12)
        worksheet.set_column('G:H', 18)
        worksheet.set_column('I:J', 10)
    
    # Feuille Programmes
    if 'programmes' in data_types:
        worksheet = workbook.add_worksheet('Programmes')
        headers = [
            'ID', 'Nom', 'Description', 'Date début', 'Date fin', 'Gestionnaire',
            'Nb binômes', 'Nb jalons', 'Taux completion', 'Statut'
        ]
        
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        for row, programme in enumerate(Programme.objects.all().order_by('date_debut'), 1):
            binomes = Binome.objects.filter(programme=programme)
            jalons = JalonBinome.objects.filter(binome__in=binomes)
            
            completion_rate = 0
            if jalons.count() > 0:
                completed = jalons.filter(statut='DONE').count()
                completion_rate = round((completed / jalons.count()) * 100, 1)
            
            # Déterminer le statut
            today = datetime.now().date()
            if programme.date_fin < today:
                statut = 'Terminé'
            elif programme.date_debut <= today <= programme.date_fin:
                statut = 'En cours'
            else:
                statut = 'À venir'
            
            worksheet.write(row, 0, programme.id, data_format)
            worksheet.write(row, 1, programme.nom, data_format)
            worksheet.write(row, 2, programme.description, data_format)
            worksheet.write(row, 3, programme.date_debut, date_format)
            worksheet.write(row, 4, programme.date_fin, date_format)
            worksheet.write(row, 5, programme.gestionnaire.username, data_format)
            worksheet.write(row, 6, binomes.count(), data_format)
            worksheet.write(row, 7, jalons.count(), data_format)
            worksheet.write(row, 8, f"{completion_rate}%", data_format)
            worksheet.write(row, 9, statut, data_format)
        
        worksheet.set_column('A:A', 5)
        worksheet.set_column('B:B', 20)
        worksheet.set_column('C:C', 30)
        worksheet.set_column('D:F', 15)
        worksheet.set_column('G:J', 12)
    
    # Feuille Statistiques
    stats_worksheet = workbook.add_worksheet('Statistiques')
    
    # Statistiques générales
    stats_data = [
        ['Métrique', 'Valeur'],
        ['Total utilisateurs', User.objects.count()],
        ['Total programmes', Programme.objects.count()],
        ['Total binômes', Binome.objects.count()],
        ['Total jalons', JalonBinome.objects.count()],
        ['Jalons complétés', JalonBinome.objects.filter(statut='DONE').count()],
        ['Jalons en attente', JalonBinome.objects.filter(statut='WAIT').count()],
        ['Jalons à faire', JalonBinome.objects.filter(statut='TODO').count()],
        ['Total feedbacks', FeedbackResponse.objects.count()],
    ]
    
    for row, (metric, value) in enumerate(stats_data):
        if row == 0:
            stats_worksheet.write(row, 0, metric, header_format)
            stats_worksheet.write(row, 1, value, header_format)
        else:
            stats_worksheet.write(row, 0, metric, data_format)
            stats_worksheet.write(row, 1, value, data_format)
    
    # Répartition par rôle
    stats_worksheet.write(len(stats_data) + 1, 0, 'Répartition par rôle', header_format)
    role_stats = User.objects.values('role').annotate(count=Count('id'))
    
    for i, stat in enumerate(role_stats):
        row = len(stats_data) + 2 + i
        role_display = dict(User.ROLE_CHOICES).get(stat['role'], stat['role'])
        stats_worksheet.write(row, 0, role_display, data_format)
        stats_worksheet.write(row, 1, stat['count'], data_format)
    
    stats_worksheet.set_column('A:A', 25)
    stats_worksheet.set_column('B:B', 15)
    
    workbook.close()
    output.seek(0)
    
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="mentorship_export_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx"'
    
    return response

@login_required
@role_required(['ADF'])
def admin_export_data(request):
    """Export rapide pour le dashboard admin"""
    return export_csv(request, ['users', 'programmes', 'binomes', 'jalons'])

@login_required
@role_required(['ADF'])
def admin_send_reminders(request):
    """Send reminder notifications manually"""
    if request.method == 'POST':
        try:
            count = EmailNotificationService.send_jalon_reminder_notifications()
            return JsonResponse({'success': True, 'count': count})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'})

@login_required
@role_required(['ADF'])
def admin_system_alerts(request):
    """Get system alerts for dashboard"""
    alerts = []
    
    # Vérifier les jalons en retard
    overdue_count = JalonBinome.objects.filter(
        statut='TODO',
        jalon__date_echeance__lt=timezone.now().date()
    ).count()
    
    if overdue_count > 0:
        alerts.append({
            'type': 'warning',
            'icon': 'exclamation-triangle',
            'title': 'Jalons en retard',
            'message': f'{overdue_count} jalon(s) ont dépassé leur échéance'
        })
    
    # Vérifier les validations en attente
    pending_count = JalonBinome.objects.filter(statut='WAIT').count()
    if pending_count > 10:
        alerts.append({
            'type': 'info',
            'icon': 'clock',
            'title': 'Validations en attente',
            'message': f'{pending_count} jalons attendent une validation'
        })
    
    # Vérifier les utilisateurs inactifs
    inactive_count = User.objects.filter(
        is_active=True,
        last_login__lt=timezone.now() - timedelta(days=30)
    ).count()
    
    if inactive_count > 0:
        alerts.append({
            'type': 'warning',
            'icon': 'user-slash',
            'title': 'Utilisateurs inactifs',
            'message': f'{inactive_count} utilisateur(s) inactif(s) depuis 30 jours'
        })
    
    # Vérifier l'espace disque (simulation)
    alerts.append({
        'type': 'success',
        'icon': 'check-circle',
        'title': 'Système opérationnel',
        'message': 'Tous les services fonctionnent normalement'
    })
    
    return JsonResponse({'alerts': alerts})

@login_required
@role_required(['ADF'])
def admin_users_data(request):
    """Get users data for dashboard table"""
    users_data = []
    
    for user in User.objects.all().order_by('-date_joined'):
        users_data.append({
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name(),
            'email': user.email,
            'role': user.role,
            'role_display': user.get_role_display(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'is_active': user.is_active,
            'date_joined': user.date_joined.isoformat()
        })
    
    return JsonResponse({'users': users_data})

@login_required
@role_required(['ADF'])
def admin_toggle_user(request, user_id):
    """Toggle user active status"""
    if request.method == 'POST':
        try:
            user = get_object_or_404(User, id=user_id)
            user.is_active = not user.is_active
            user.save()
            
            return JsonResponse({
                'success': True, 
                'is_active': user.is_active,
                'message': f'Utilisateur {"activé" if user.is_active else "désactivé"}'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'})

@login_required
def feedback_form(request):
    """Vue générale pour les formulaires de feedback"""
    if request.user.role not in ['RH', 'MENTOR', 'MENTEE']:
        messages.error(request, "Accès non autorisé.")
        return redirect('dashboard')
    
    # Pour les RH : voir tous les formulaires
    if request.user.role == 'RH':
        forms = FeedbackForm.objects.all().order_by('-date_creation')
        return render(request, 'feedback/manage_forms.html', {'forms': forms})
    
    # Pour les mentors/mentorés : voir les formulaires à remplir
    available_forms = FeedbackForm.objects.all()
    completed_forms = FeedbackResponse.objects.filter(user=request.user).values_list('form_id', flat=True)
    pending_forms = available_forms.exclude(id__in=completed_forms)
    
    context = {
        'pending_forms': pending_forms,
        'completed_forms': available_forms.filter(id__in=completed_forms),
    }
    return render(request, 'feedback/user_forms.html', context)

@login_required
@role_required(['RH', 'ADF'])
def programmes_list(request):
    """Liste des programmes pour RH et ADF"""
    programmes = Programme.objects.all().select_related('gestionnaire').order_by('-date_debut')
    
    # Ajouter des statistiques pour chaque programme
    for programme in programmes:
        binomes = Binome.objects.filter(programme=programme)
        jalons = JalonBinome.objects.filter(binome__in=binomes)
        
        programme.binomes_count = binomes.count()
        programme.jalons_total = jalons.count()
        programme.jalons_completed = jalons.filter(statut='DONE').count()
        
        if programme.jalons_total > 0:
            programme.completion_rate = round((programme.jalons_completed / programme.jalons_total) * 100, 1)
        else:
            programme.completion_rate = 0
    
    context = {
        'programmes': programmes,
    }
    return render(request, 'programmes_list.html', context)

@login_required
@role_required(['RH', 'ADF'])
def manage_rh(request):
    """Gestion des utilisateurs RH"""
    if request.method == 'POST':
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')
        
        if action == 'toggle_active' and user_id:
            user = get_object_or_404(User, id=user_id)
            user.is_active = not user.is_active
            user.save()
            messages.success(request, f"Utilisateur {user.username} {'activé' if user.is_active else 'désactivé'}")
        
        elif action == 'change_role' and user_id:
            user = get_object_or_404(User, id=user_id)
            new_role = request.POST.get('new_role')
            if new_role in dict(User.ROLE_CHOICES):
                user.role = new_role
                user.save()
                messages.success(request, f"Rôle de {user.username} changé vers {user.get_role_display()}")
    
    # Statistiques des utilisateurs
    users = User.objects.all().order_by('-date_joined')
    user_stats = {
        'total': users.count(),
        'active': users.filter(is_active=True).count(),
        'mentors': users.filter(role='MENTOR').count(),
        'mentees': users.filter(role='MENTEE').count(),
        'rh': users.filter(role='RH').count(),
        'adf': users.filter(role='ADF').count(),
    }
    
    context = {
        'users': users,
        'user_stats': user_stats,
        'role_choices': User.ROLE_CHOICES,
    }
    return render(request, 'manage_rh.html', context)

@login_required
@role_required(['RH', 'ADF'])
def global_stats(request):
    """Statistiques globales de la plateforme"""
    from django.db.models import Avg, Count, Q
    
    # Statistiques générales
    stats = {
        'users': {
            'total': User.objects.count(),
            'active': User.objects.filter(is_active=True).count(),
            'mentors': User.objects.filter(role='MENTOR').count(),
            'mentees': User.objects.filter(role='MENTEE').count(),
            'rh': User.objects.filter(role='RH').count(),
        },
        'programmes': {
            'total': Programme.objects.count(),
            'active': Programme.objects.filter(
                date_debut__lte=timezone.now().date(),
                date_fin__gte=timezone.now().date()
            ).count(),
        },
        'binomes': {
            'total': Binome.objects.count(),
        },
        'jalons': {
            'total': JalonBinome.objects.count(),
            'completed': JalonBinome.objects.filter(statut='DONE').count(),
            'pending': JalonBinome.objects.filter(statut='WAIT').count(),
            'todo': JalonBinome.objects.filter(statut='TODO').count(),
            'overdue': JalonBinome.objects.filter(
                statut='TODO',
                jalon__date_echeance__lt=timezone.now().date()
            ).count(),
        }
    }
    
    # Calcul du taux de completion global
    if stats['jalons']['total'] > 0:
        stats['jalons']['completion_rate'] = round(
            (stats['jalons']['completed'] / stats['jalons']['total']) * 100, 1
        )
    else:
        stats['jalons']['completion_rate'] = 0
    
    # Statistiques par programme
    programme_stats = []
    for programme in Programme.objects.all():
        binomes = Binome.objects.filter(programme=programme)
        jalons = JalonBinome.objects.filter(binome__in=binomes)
        
        prog_stat = {
            'programme': programme,
            'binomes_count': binomes.count(),
            'jalons_total': jalons.count(),
            'jalons_completed': jalons.filter(statut='DONE').count(),
            'completion_rate': 0,
        }
        
        if prog_stat['jalons_total'] > 0:
            prog_stat['completion_rate'] = round(
                (prog_stat['jalons_completed'] / prog_stat['jalons_total']) * 100, 1
            )
        
        programme_stats.append(prog_stat)
    
    # Activité récente (30 derniers jours)
    last_month = timezone.now() - timedelta(days=30)
    recent_activity = {
        'new_users': User.objects.filter(date_joined__gte=last_month).count(),
        'completed_jalons': JalonBinome.objects.filter(
            date_validation__gte=last_month
        ).count(),
        'new_feedbacks': FeedbackResponse.objects.filter(
            date_reponse__gte=last_month
        ).count(),
    }
    
    context = {
        'stats': stats,
        'programme_stats': programme_stats,
        'recent_activity': recent_activity,
    }
    return render(request, 'global_stats.html', context)
