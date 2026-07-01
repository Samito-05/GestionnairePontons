from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from pontons.models import Ponton, Embarcation, Location, UserProfile


class Command(BaseCommand):
    help = 'Initialise les données de démonstration'

    def handle(self, *args, **options):
        from django.conf import settings
        if not settings.DEBUG:
            raise CommandError(
                "init_demo ne doit PAS tourner en production (DEBUG=False). "
                "Forcez avec --settings=... si vous êtes sûr."
            )
        self.stdout.write('Création des données de démo...')

        # Pontons
        p1, _ = Ponton.objects.get_or_create(nom='Ponton A', defaults={'ordre': 1, 'description': 'Ponton principal'})
        p2, _ = Ponton.objects.get_or_create(nom='Ponton B', defaults={'ordre': 2, 'description': 'Ponton secondaire'})

        # Embarcations
        embarcations_data = [
            ('Pédalo 1', 'pedalo', p1, '#3273dc', 1),
            ('Pédalo 2', 'pedalo', p1, '#209cee', 2),
            ('Pédalo 3', 'pedalo', p1, '#00d1b2', 3),
            ('Kayak Rouge', 'kayak', p1, '#ff3860', 4),
            ('Kayak Vert', 'kayak', p1, '#23d160', 5),
            ('Canoë 1', 'canoe', p2, '#ff6b35', 1),
            ('Canoë 2', 'canoe', p2, '#f7931e', 2),
            ('SUP 1', 'sup', p2, '#9b59b6', 3),
            ('SUP 2', 'sup', p2, '#8e44ad', 4),
            ('Barque 1', 'barque', p2, '#795548', 5),
        ]

        embs = []
        for nom, typ, ponton, couleur, ordre in embarcations_data:
            emb, _ = Embarcation.objects.get_or_create(
                nom=nom,
                defaults={'type_embarcation': typ, 'ponton': ponton, 'couleur': couleur, 'ordre': ordre}
            )
            embs.append(emb)

        # Utilisateurs
        # Utilisateurs de démo — idempotent : crée si absent, force toujours le rôle.
        # Le signal post_save crée déjà un UserProfile ; update_or_create l'ajuste.
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={'email': 'admin@pontons.local', 'is_staff': True, 'is_superuser': True},
        )
        if created:
            admin.set_password('admin123')
            admin.save()
            self.stdout.write('  Superuser admin créé (mdp: admin123)')
        UserProfile.objects.update_or_create(user=admin, defaults={'role': 'admin'})

        g1, created = User.objects.get_or_create(
            username='gestionnaire1',
            defaults={'first_name': 'Jean', 'last_name': 'Dupont'},
        )
        if created:
            g1.set_password('gest123')
            g1.save()
            self.stdout.write('  Gestionnaire gestionnaire1 créé (mdp: gest123)')
        UserProfile.objects.update_or_create(user=g1, defaults={'role': 'gestionnaire'})

        v1, created = User.objects.get_or_create(
            username='visiteur1',
            defaults={'first_name': 'Marie', 'last_name': 'Martin'},
        )
        if created:
            v1.set_password('visit123')
            v1.save()
            self.stdout.write('  Visiteur visiteur1 créé (mdp: visit123)')
        UserProfile.objects.update_or_create(user=v1, defaults={'role': 'visiteur'})

        # Locations de démo pour aujourd'hui
        now = timezone.now()
        today_13h = now.replace(hour=13, minute=0, second=0, microsecond=0)
        demo_user = User.objects.filter(username='gestionnaire1').first() or User.objects.first()

        locations_demo = [
            (embs[0], today_13h, today_13h + timedelta(hours=1)),
            (embs[1], today_13h + timedelta(hours=1), today_13h + timedelta(hours=2)),
            (embs[3], today_13h + timedelta(minutes=30), today_13h + timedelta(hours=1, minutes=30)),
            (embs[5], today_13h + timedelta(hours=2), today_13h + timedelta(hours=3)),
            (embs[7], today_13h + timedelta(hours=3), today_13h + timedelta(hours=4)),
        ]

        for emb, debut, fin in locations_demo:
            if not Location.objects.filter(embarcation=emb, heure_debut=debut).exists():
                Location.objects.create(
                    embarcation=emb,
                    gestionnaire=demo_user,
                    heure_debut=debut,
                    heure_fin=fin,
                    notes='Démo',
                )

        self.stdout.write(self.style.SUCCESS('Données de démo créées avec succès !'))
        self.stdout.write('')
        self.stdout.write('  Comptes disponibles :')
        self.stdout.write('  admin / admin123          (Superadmin)')
        self.stdout.write('  gestionnaire1 / gest123   (Gestionnaire)')
        self.stdout.write('  visiteur1 / visit123      (Visiteur)')
