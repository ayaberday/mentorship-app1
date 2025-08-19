from django.contrib import admin
from django.urls import path
from accounts import views
from django.contrib.auth.views import LoginView

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    path('jalons/', views.jalons_timeline, name='jalons_timeline'),
    path('jalons/realise/<int:jalonbinome_id>/', views.jalon_realise, name='jalon_realise'),
    path('jalons/valide/<int:jalonbinome_id>/', views.jalon_valide, name='jalon_valide'),
    path('jalons/binomes/', views.binomes_list, name='binomes_list'),
    path('jalons/feedback/', views.feedback_form, name='feedback_form'),
    
    path('jalons/feedback/create/', views.create_feedback_form, name='create_feedback_form'),
    path('jalons/feedback/<int:form_id>/edit/', views.edit_feedback_form, name='edit_feedback_form'),
    path('jalons/feedback/<int:form_id>/fill/', views.fill_feedback_form, name='fill_feedback_form'),
    path('jalons/feedback/<int:form_id>/results/', views.feedback_results, name='feedback_results'),

    path('admin/', admin.site.urls),

    # Authentication URLs
    path('login/', views.custom_login, name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('signup/', views.signup, name='signup'),
    path('accounts/profile/', views.dashboard, name='profile'),
    
    path('mentores/', views.mentores_list, name='mentores_list'),
    
    path('programmes/', views.programmes_list, name='programmes_list'),
    
    path('manage-rh/', views.manage_rh, name='manage_rh'),
    path('stats/', views.global_stats, name='global_stats'),
    
    path('export/', views.export_data, name='export_data'),
    path('superadmin/export/', views.admin_export_data, name='admin_export_data'),
    path('superadmin/send-reminders/', views.admin_send_reminders, name='admin_send_reminders'),
    path('superadmin/system-alerts/', views.admin_system_alerts, name='admin_system_alerts'),
    path('superadmin/users-data/', views.admin_users_data, name='admin_users_data'),
    path('admin/toggle-user/<int:user_id>/', views.admin_toggle_user, name='admin_toggle_user'),
]
