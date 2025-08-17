from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model, logout
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q
from functools import wraps
from datetime import datetime, timedelta
from .forms import CustomUserCreationForm
from .models import User, Programme, Binome, Jalon, JalonBinome, FeedbackForm

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

@login_required
def dashboard(request):
    user = request.user
    context = {}

    if user.role == 'ADF':
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
            for jalon in validated_jalons:
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
        messages.success(request, "Jalon marqué comme réalisé. En attente de validation du mentor.")
        # TODO: Send email notification to mentor
    
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
        messages.success(request, "Jalon validé.")
        # TODO: Send email notification to mentee
    
    return redirect('jalons_timeline')

@login_required
@role_required(['MENTOR'])
def mentores_list(request):
    """List mentees for a mentor"""
    binomes = Binome.objects.filter(mentor=request.user).select_related('mentore', 'programme')
    return render(request, 'mentores_list.html', {'binomes': binomes})

@login_required
@role_required(['MENTOR', 'MENTEE'])
def feedback_form(request):
    """Handle feedback forms"""
    # TODO: Implement feedback form logic
    return render(request, 'feedback_form.html', {})

@login_required
@role_required(['RH'])
def programmes_list(request):
    """List all programmes for RH"""
    programmes = Programme.objects.all().annotate(
        binomes_count=Count('binome')
    )
    return render(request, 'programmes_list.html', {'programmes': programmes})

@login_required
@role_required(['RH'])
def binomes_list(request):
    """List all binomes for RH"""
    binomes = Binome.objects.all().select_related('mentor', 'mentore', 'programme')
    return render(request, 'binomes_list.html', {'binomes': binomes})

@login_required
@role_required(['ADF'])
def manage_rh(request):
    """Manage RH users for Super Admin"""
    rh_users = User.objects.filter(role='RH')
    return render(request, 'manage_rh.html', {'rh_users': rh_users})

@login_required
@role_required(['ADF'])
def global_stats(request):
    """Enhanced global statistics for Super Admin with trends and analytics"""
    
    # Basic statistics
    basic_stats = {
        'total_users': User.objects.count(),
        'total_programmes': Programme.objects.count(),
        'total_binomes': Binome.objects.count(),
        'jalons_stats': JalonBinome.objects.aggregate(
            total=Count('id'),
            done=Count('id', filter=Q(statut='DONE')),
            wait=Count('id', filter=Q(statut='WAIT')),
            todo=Count('id', filter=Q(statut='TODO'))
        )
    }
    
    # User growth over time (last 6 months)
    six_months_ago = timezone.now() - timedelta(days=180)
    monthly_user_growth = []
    for i in range(6):
        month_start = six_months_ago + timedelta(days=30*i)
        month_end = month_start + timedelta(days=30)
        users_count = User.objects.filter(
            date_joined__gte=month_start,
            date_joined__lt=month_end
        ).count()
        monthly_user_growth.append({
            'month': month_start.strftime('%B'),
            'count': users_count
        })
    
    # Programme effectiveness
    programme_effectiveness = []
    for programme in Programme.objects.all():
        binomes = Binome.objects.filter(programme=programme)
        jalons = JalonBinome.objects.filter(binome__in=binomes)
        
        effectiveness = {
            'programme': programme.nom,
            'binomes_count': binomes.count(),
            'jalons_total': jalons.count(),
            'jalons_completed': jalons.filter(statut='DONE').count(),
            'completion_rate': 0,
            'avg_time_to_complete': 0
        }
        
        if jalons.count() > 0:
            effectiveness['completion_rate'] = round(
                (effectiveness['jalons_completed'] / effectiveness['jalons_total']) * 100, 1
            )
        
        # Calculate average time to complete jalons
        completed_jalons = jalons.filter(
            statut='DONE',
            date_realisation__isnull=False,
            date_validation__isnull=False
        )
        if completed_jalons.exists():
            total_days = 0
            count = 0
            for jalon in completed_jalons:
                if jalon.binome.date_creation:
                    days = (jalon.date_validation.date() - jalon.binome.date_creation).days
                    total_days += days
                    count += 1
            if count > 0:
                effectiveness['avg_time_to_complete'] = round(total_days / count, 1)
        
        programme_effectiveness.append(effectiveness)
    
    # Mentor performance metrics
    mentor_performance = []
    mentors = User.objects.filter(role='MENTOR')
    for mentor in mentors:
        binomes = Binome.objects.filter(mentor=mentor)
        jalons = JalonBinome.objects.filter(binome__in=binomes)
        
        # Response time for validations
        validated_jalons = jalons.filter(
            statut='DONE',
            date_realisation__isnull=False,
            date_validation__isnull=False
        )
        
        avg_response_time = 0
        if validated_jalons.exists():
            total_response_time = 0
            for jalon in validated_jalons:
                delta = jalon.date_validation - jalon.date_realisation
                total_response_time += delta.days
            avg_response_time = round(total_response_time / validated_jalons.count(), 1)
        
        mentor_performance.append({
            'mentor': mentor.get_full_name() or mentor.username,
            'mentees_count': binomes.count(),
            'jalons_validated': validated_jalons.count(),
            'avg_response_time': avg_response_time,
            'pending_validations': jalons.filter(statut='WAIT').count()
        })
    
    # System health indicators
    last_week = timezone.now() - timedelta(days=7)
    health_indicators = {
        'active_users_week': User.objects.filter(last_login__gte=last_week).count(),
        'jalons_completed_week': JalonBinome.objects.filter(
            date_validation__gte=last_week
        ).count(),
        'overdue_jalons': JalonBinome.objects.filter(
            statut='TODO',
            jalon__date_echeance__lt=timezone.now().date()
        ).count(),
        'stalled_binomes': Binome.objects.exclude(
            id__in=JalonBinome.objects.filter(
                date_realisation__gte=timezone.now() - timedelta(days=30)
            ).values_list('binome_id', flat=True)
        ).count()
    }
    
    context = {
        'stats': basic_stats,
        'monthly_user_growth': monthly_user_growth,
        'programme_effectiveness': programme_effectiveness,
        'mentor_performance': mentor_performance,
        'health_indicators': health_indicators,
    }
    
    return render(request, 'global_stats.html', context)
