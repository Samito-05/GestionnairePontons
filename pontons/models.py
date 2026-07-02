from django.core.validators import RegexValidator
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
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
        ('pedalo', 'Pédalo'),
        ('kayak', 'Kayak'),
        ('canoe', 'Canoë'),
        ('barque', 'Barque'),
        ('sup', 'Stand Up Paddle'),
        ('autre', 'Autre'),
    ]

    nom = models.CharField(max_length=100)
    type_embarcation = models.CharField(max_length=20, choices=TYPE_CHOICES, default='pedalo')
    ponton = models.ForeignKey(Ponton, on_delete=models.CASCADE, related_name='embarcations')
    couleur = models.CharField(
        max_length=7, default='#3273dc', help_text='Couleur hex ex: #3273dc',
        validators=[RegexValidator(r'^#[0-9a-fA-F]{6}$', 'Couleur hex invalide (format #RRGGBB).')],
    )
    actif = models.BooleanField(default=True)
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['ponton', 'ordre', 'nom']
        verbose_name = 'Embarcation'
        verbose_name_plural = 'Embarcations'

    def __str__(self):
        return f"{self.nom} ({self.ponton.nom})"

    def est_louee_maintenant(self):
        if hasattr(self, 'est_louee_now'):
            return self.est_louee_now
        now = timezone.now()
        # localdate() : date en TZ locale — now.date() serait la date UTC (bug autour de minuit)
        today = timezone.localdate()
        # reservee: pas d'expiration temporelle (valide toute la journée jusqu'au sortir)
        # sortie: actif tant que non retournée (returned_at) — dépassement inclus
        return (
            self.locations.filter(statut='reservee', heure_debut__date=today, returned_at__isnull=True).exists() or
            self.locations.filter(statut='sortie', heure_debut__lte=now, returned_at__isnull=True).exists()
        )

    def location_en_cours(self):
        if hasattr(self, 'locations_actives'):
            # prefetch déjà filtré (voir gestionnaire view)
            for loc in self.locations_actives:
                if loc.statut == 'reservee':
                    return loc
            return self.locations_actives[0] if self.locations_actives else None
        now = timezone.now()
        # reservee d'aujourd'hui prime — pas de contrainte horaire
        # (localdate — pas now.date() qui renvoie la date UTC)
        loc = self.locations.filter(
            statut='reservee', heure_debut__date=timezone.localdate(), returned_at__isnull=True
        ).order_by('-created_at').first()
        if loc:
            return loc
        # sortie active — reste sortie jusqu'au retour effectif (dépassement inclus)
        return self.locations.filter(
            statut='sortie', heure_debut__lte=now, returned_at__isnull=True
        ).first()


class Location(models.Model):
    STATUT_CHOICES = [
        ('reservee', 'Réservée'),
        ('sortie', 'Sortie'),
    ]

    embarcation = models.ForeignKey(Embarcation, on_delete=models.CASCADE, related_name='locations')
    gestionnaire = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='locations')
    heure_debut = models.DateTimeField()
    heure_fin = models.DateTimeField()
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default='reservee')
    is_manual = models.BooleanField(default=False, help_text='Créée manuellement via admin (heure_fin fixe)')
    returned_at = models.DateTimeField(null=True, blank=True, help_text='Retour effectif — null tant que non retournée (dépassement possible)')
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['heure_debut']
        verbose_name = 'Location'
        verbose_name_plural = 'Locations'
        indexes = [
            models.Index(fields=['heure_debut']),
            models.Index(fields=['embarcation', 'heure_debut']),
        ]

    def __str__(self):
        return f"{self.embarcation.nom} — {self.heure_debut.strftime('%d/%m %H:%M')}"

    def save(self, *args, **kwargs):
        if not self.heure_fin:
            self.heure_fin = self.heure_debut + timedelta(hours=1)
        super().save(*args, **kwargs)

    @property
    def duree_minutes(self):
        return int((self.heure_fin - self.heure_debut).total_seconds() / 60)

    def is_overtime(self):
        """True si sortie non retournée et l'heure de fin prévue est dépassée."""
        return bool(
            self.statut == 'sortie' and self.returned_at is None
            and self.heure_fin and timezone.now() > self.heure_fin
        )

    @property
    def overtime_minutes(self):
        if not self.is_overtime():
            return 0
        return int((timezone.now() - self.heure_fin).total_seconds() / 60)

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


# ─── Signals ─────────────────────────────────────────────────────────────────

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Auto-create UserProfile for every new User."""
    if created:
        UserProfile.objects.get_or_create(user=instance)
