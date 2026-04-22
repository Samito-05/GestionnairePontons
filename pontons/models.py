from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


class Ponton(models.Model):
    nom = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    ordre = models.PositiveIntegerField(default=0)
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ['ordre', 'nom']
        verbose_name = 'Ponton'
        verbose_name_plural = 'Pontons'

    def __str__(self):
        return self.nom


class Embarcation(models.Model):
    TYPE_CHOICES = [
        ('pedalo', 'Pédaleau'),
        ('kayak', 'Kayak'),
        ('canoe', 'Canoë'),
        ('barque', 'Barque'),
        ('sup', 'Stand Up Paddle'),
        ('autre', 'Autre'),
    ]

    nom = models.CharField(max_length=100)
    type_embarcation = models.CharField(max_length=20, choices=TYPE_CHOICES, default='pedalo')
    ponton = models.ForeignKey(Ponton, on_delete=models.CASCADE, related_name='embarcations')
    couleur = models.CharField(max_length=7, default='#3273dc', help_text='Couleur hex ex: #3273dc')
    actif = models.BooleanField(default=True)
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['ponton', 'ordre', 'nom']
        verbose_name = 'Embarcation'
        verbose_name_plural = 'Embarcations'

    def __str__(self):
        return f"{self.nom} ({self.ponton.nom})"

    def est_louee_maintenant(self):
        now = timezone.now()
        return self.locations.filter(heure_debut__lte=now, heure_fin__gt=now).exists()

    def location_en_cours(self):
        now = timezone.now()
        return self.locations.filter(heure_debut__lte=now, heure_fin__gt=now).first()


class Location(models.Model):
    embarcation = models.ForeignKey(Embarcation, on_delete=models.CASCADE, related_name='locations')
    gestionnaire = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='locations')
    heure_debut = models.DateTimeField()
    heure_fin = models.DateTimeField()
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['heure_debut']
        verbose_name = 'Location'
        verbose_name_plural = 'Locations'

    def __str__(self):
        return f"{self.embarcation.nom} — {self.heure_debut.strftime('%d/%m %H:%M')}"

    def save(self, *args, **kwargs):
        if not self.heure_fin:
            self.heure_fin = self.heure_debut + timedelta(hours=1)
        super().save(*args, **kwargs)

    @property
    def duree_minutes(self):
        return int((self.heure_fin - self.heure_debut).total_seconds() / 60)

    @property
    def slot_debut(self):
        """Index dans la grille 13h–20h par tranches de 30 min."""
        h = self.heure_debut.hour
        m = self.heure_debut.minute
        return (h - 13) * 2 + (1 if m >= 30 else 0)

    @property
    def slot_duree(self):
        return max(1, self.duree_minutes // 30)


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Administrateur'),
        ('gestionnaire', 'Gestionnaire'),
        ('visiteur', 'Visiteur'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='visiteur')

    class Meta:
        verbose_name = 'Profil utilisateur'
        verbose_name_plural = 'Profils utilisateurs'

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    def is_admin(self):
        return self.role == 'admin' or self.user.is_superuser

    def is_gestionnaire(self):
        return self.role in ('admin', 'gestionnaire') or self.user.is_superuser
