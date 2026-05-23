from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pontons', '0002_location_pontons_loc_heure_d_98dd20_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='location',
            name='statut',
            field=models.CharField(
                choices=[('reservee', 'Réservée'), ('sortie', 'Sortie')],
                default='reservee',
                max_length=10,
            ),
        ),
    ]
