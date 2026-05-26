from django.core.management.base import BaseCommand
from pontons.models import Ponton, Embarcation


class Command(BaseCommand):
    help = 'Peuple la BDD avec 4 pontons et 18 embarcations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--flush',
            action='store_true',
            help='Supprime les pontons et embarcations existants avant de créer',
        )

    def handle(self, *args, **options):
        if options['flush']:
            Embarcation.objects.all().delete()
            Ponton.objects.all().delete()
            self.stdout.write(self.style.WARNING('Données existantes supprimées.'))

        # ── Pontons (1 par type) ──────────────────────────────────────────────
        ponton_pedalos_4p, _ = Ponton.objects.get_or_create(
            nom='Ponton Pédalos 4 places',
            defaults={'ordre': 1, 'description': 'Pédalos 4 places'},
        )
        ponton_pedalos_2p, _ = Ponton.objects.get_or_create(
            nom='Ponton Pédalos 2 places',
            defaults={'ordre': 2, 'description': 'Pédalos 2 places'},
        )
        ponton_kayaks, _ = Ponton.objects.get_or_create(
            nom='Ponton Kayaks',
            defaults={'ordre': 3, 'description': 'Kayaks'},
        )
        ponton_paddles, _ = Ponton.objects.get_or_create(
            nom='Ponton Paddles',
            defaults={'ordre': 4, 'description': 'Stand Up Paddles'},
        )

        self.stdout.write('Pontons créés.')

        # ── Embarcations ──────────────────────────────────────────────────────
        # Palette de couleurs par type
        couleurs_pedalo_4p = [
            '#1565C0', '#1976D2', '#1E88E5', '#2196F3',
            '#42A5F5', '#64B5F6', '#90CAF9',
        ]
        couleurs_pedalo_2p = [
            '#00838F', '#00ACC1', '#00BCD4', '#26C6DA',
        ]
        couleurs_kayak = [
            '#C62828', '#E53935', '#F44336',
        ]
        couleurs_paddle = [
            '#2E7D32', '#388E3C', '#43A047', '#4CAF50',
        ]

        embarcations = []

        # 7 pédalos 4 places
        for i in range(1, 8):
            emb, created = Embarcation.objects.get_or_create(
                nom=f'Pédalo 4P {i}',
                defaults={
                    'type_embarcation': 'pedalo',
                    'ponton': ponton_pedalos_4p,
                    'couleur': couleurs_pedalo_4p[i - 1],
                    'ordre': i,
                },
            )
            embarcations.append((emb, created))

        # 4 pédalos 2 places
        for i in range(1, 5):
            emb, created = Embarcation.objects.get_or_create(
                nom=f'Pédalo 2P {i}',
                defaults={
                    'type_embarcation': 'pedalo',
                    'ponton': ponton_pedalos_2p,
                    'couleur': couleurs_pedalo_2p[i - 1],
                    'ordre': i,
                },
            )
            embarcations.append((emb, created))

        # 3 kayaks
        for i in range(1, 4):
            emb, created = Embarcation.objects.get_or_create(
                nom=f'Kayak {i}',
                defaults={
                    'type_embarcation': 'kayak',
                    'ponton': ponton_kayaks,
                    'couleur': couleurs_kayak[i - 1],
                    'ordre': i,
                },
            )
            embarcations.append((emb, created))

        # 4 paddles (SUP)
        for i in range(1, 5):
            emb, created = Embarcation.objects.get_or_create(
                nom=f'Paddle {i}',
                defaults={
                    'type_embarcation': 'sup',
                    'ponton': ponton_paddles,
                    'couleur': couleurs_paddle[i - 1],
                    'ordre': i,
                },
            )
            embarcations.append((emb, created))

        # ── Résumé ────────────────────────────────────────────────────────────
        created_count = sum(1 for _, c in embarcations if c)
        skipped_count = sum(1 for _, c in embarcations if not c)

        self.stdout.write(self.style.SUCCESS(
            f'Terminé : {created_count} embarcation(s) créée(s), '
            f'{skipped_count} déjà existante(s) ignorée(s).'
        ))
        self.stdout.write('')
        self.stdout.write('  Ponton Pédalos 4 places → 7 pédalos 4P')
        self.stdout.write('  Ponton Pédalos 2 places → 4 pédalos 2P')
        self.stdout.write('  Ponton Kayaks           → 3 kayaks')
        self.stdout.write('  Ponton Paddles          → 4 paddles (SUP)')
