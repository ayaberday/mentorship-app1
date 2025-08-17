from django.contrib import admin
from .models import User, Programme, Jalon, Binome

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
	list_display = ('username', 'email', 'role', 'is_active', 'is_staff')
	list_filter = ('role', 'is_active', 'is_staff')
	search_fields = ('username', 'email')

@admin.register(Programme)
class ProgrammeAdmin(admin.ModelAdmin):
	list_display = ('nom', 'gestionnaire', 'date_debut', 'date_fin')
	search_fields = ('nom', 'description')
	list_filter = ('date_debut', 'date_fin')

@admin.register(Jalon)
class JalonAdmin(admin.ModelAdmin):
	list_display = ('titre', 'programme', 'date_echeance')
	search_fields = ('titre', 'description')
	list_filter = ('date_echeance', 'programme')

@admin.register(Binome)
class BinomeAdmin(admin.ModelAdmin):
	list_display = ('programme', 'mentor', 'mentore')
	list_filter = ('programme',)
	search_fields = ('mentor__username', 'mentore__username')
