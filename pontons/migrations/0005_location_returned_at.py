from django.db import migrations, models
from django.db.models import F
from django.utils import timezone


def backfill_returned_at(apps, schema_editor):
    """Anciennes sorties dont l'heure de fin est déjà passée = considérées retournées.
    Les sorties encore actives (heure_fin future) restent null → toujours dehors."""
    Location = apps.get_model('pontons', 'Location')
    now = timezone.now()
    Location.objects.filter(
        statut='sortie', heure_fin__lte=now, returned_at__isnull=True
    ).update(returned_at=F('heure_fin'))


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('pontons', '0004_location_is_manual'),
    ]

    operations = [
        migrations.AddField(
            model_name='location',
            name='returned_at',
            field=models.DateTimeField(
                blank=True, null=True,
                help_text='Retour effectif — null tant que non retournée (dépassement possible)',
            ),
        ),
        migrations.RunPython(backfill_returned_at, noop),
    ]
