from django.contrib import admin
from django.utils.html import format_html
from .models import Ponton, Embarcation, Location, UserProfile


@admin.register(Ponton)
class PontonAdmin(admin.ModelAdmin):
    list_display = ['nom', 'ordre', 'actif', 'nb_embarcations']
    list_editable = ['ordre', 'actif']
    search_fields = ['nom']

    def nb_embarcations(self, obj):
        return obj.embarcations.count()
    nb_embarcations.short_description = 'Embarcations'


@admin.register(Embarcation)
class EmbarcationAdmin(admin.ModelAdmin):
    list_display = ['nom', 'type_embarcation', 'ponton', 'couleur_preview', 'actif', 'ordre', 'statut_live']
    list_editable = ['ordre', 'actif']
    list_filter = ['ponton', 'type_embarcation', 'actif']
    search_fields = ['nom']

    def couleur_preview(self, obj):
        return format_html(
            '<span style="display:inline-block;width:20px;height:20px;border-radius:50%;background:{};border:1px solid #ccc;"></span>',
            obj.couleur
        )
    couleur_preview.short_description = 'Couleur'

    def statut_live(self, obj):
        if obj.est_louee_maintenant():
            return format_html('<span style="color:red;font-weight:bold;">● Sortie</span>')
        return format_html('<span style="color:green;">● Dispo</span>')
    statut_live.short_description = 'Statut'


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['embarcation', 'heure_debut', 'heure_fin', 'gestionnaire', 'notes']
    list_filter = ['embarcation__ponton', 'embarcation']
    search_fields = ['embarcation__nom', 'notes']
    date_hierarchy = 'heure_debut'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role']
    list_editable = ['role']
    list_filter = ['role']
