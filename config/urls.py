from django.contrib import admin
from django.urls import path
from accounts import views
from django.contrib.auth.views import LoginView

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('jalons/', views.jalons_timeline, name='jalons_timeline'),
    path('jalon/<int:jalonbinome_id>/realise/', views.jalon_realise, name='jalon_realise'),
    path('jalon/<int:jalonbinome_id>/valide/', views.jalon_valide, name='jalon_valide'),

    path('admin/', admin.site.urls),

    # Authentication URLs
    path('login/', LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('signup/', views.signup, name='signup'),
    path('accounts/profile/', views.dashboard, name='profile'),
    
    path('mentores/', views.mentores_list, name='mentores_list'),
    path('feedback/', views.feedback_form, name='feedback_form'),
    
    path('programmes/', views.programmes_list, name='programmes_list'),
    path('binomes/', views.binomes_list, name='binomes_list'),
    
    path('manage-rh/', views.manage_rh, name='manage_rh'),
    path('stats/', views.global_stats, name='global_stats'),
]
