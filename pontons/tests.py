from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from pontons.models import Ponton, Embarcation, Location, UserProfile


# client.login() appelle authenticate() sans requête, ce que le backend django-axes
# refuse (AxesBackendRequestParameterRequired). force_login contourne l'authentification :
# ces tests portent sur les rôles et les locations, pas sur le formulaire de connexion.
MODEL_BACKEND = 'django.contrib.auth.backends.ModelBackend'


class OverlapTest(TestCase):
    def setUp(self):
        p = Ponton.objects.create(nom='P1', ordre=1)
        self.emb = Embarcation.objects.create(nom='K1', type_embarcation='kayak', ponton=p)
        self.user = User.objects.create_user('g1', password='pass')
        # Signal auto-creates profile (role='visiteur'); update to gestionnaire
        UserProfile.objects.update_or_create(user=self.user, defaults={'role': 'gestionnaire'})
        now_utc = timezone.now().replace(minute=0, second=0, microsecond=0)
        self.now_utc = now_utc
        # Form strings must be in local time (make_aware interprets as Europe/Paris)
        self.now_local = timezone.localtime(now_utc)
        Location.objects.create(
            embarcation=self.emb, gestionnaire=self.user,
            heure_debut=now_utc, heure_fin=now_utc + timedelta(hours=1)
        )

    def test_overlap_blocked_by_form(self):
        from pontons.forms import LocationForm
        form = LocationForm(data={
            'embarcation': self.emb.pk,
            'heure_debut': (self.now_local + timedelta(minutes=30)).strftime('%Y-%m-%dT%H:%M'),
            'heure_fin':   (self.now_local + timedelta(minutes=90)).strftime('%Y-%m-%dT%H:%M'),
            'statut': 'sortie',
        })
        self.assertFalse(form.is_valid())
        # Le rejet vient bien du chevauchement, pas d'un champ manquant
        self.assertIn('déjà réservée', str(form.non_field_errors()))

    def test_no_overlap_allowed(self):
        from pontons.forms import LocationForm
        form = LocationForm(data={
            'embarcation': self.emb.pk,
            'heure_debut': (self.now_local + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M'),
            'heure_fin':   (self.now_local + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M'),
            'statut': 'sortie',
        })
        self.assertTrue(form.is_valid(), form.errors)


class RoleAccessTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.visiteur = User.objects.create_user('v1', password='pass')
        # Signal auto-creates profile with default role='visiteur' — nothing extra needed

    def test_gestionnaire_view_blocked_for_visiteur(self):
        self.client.force_login(self.visiteur, backend=MODEL_BACKEND)
        resp = self.client.get('/gestionnaire/')
        self.assertRedirects(resp, '/planning/')

    def test_admin_view_blocked_for_visiteur(self):
        self.client.force_login(self.visiteur, backend=MODEL_BACKEND)
        resp = self.client.get('/gestion/')
        self.assertRedirects(resp, '/planning/')


class UserProfileSignalTest(TestCase):
    def test_profile_created_on_user_create(self):
        user = User.objects.create_user('newuser', password='pass')
        self.assertTrue(UserProfile.objects.filter(user=user).exists())


class QuickRentalAtomicTest(TestCase):
    def setUp(self):
        p = Ponton.objects.create(nom='P1', ordre=1)
        self.emb = Embarcation.objects.create(nom='K1', type_embarcation='kayak', ponton=p)
        self.gestionnaire = User.objects.create_user('gest', password='pass')
        # Signal creates profile with role='visiteur'; elevate to gestionnaire
        UserProfile.objects.update_or_create(
            user=self.gestionnaire, defaults={'role': 'gestionnaire'}
        )
        self.client = Client()
        self.client.force_login(self.gestionnaire, backend=MODEL_BACKEND)

    def test_quick_rental_creates_location(self):
        self.client.post(f'/gestionnaire/louer/{self.emb.pk}/', {'notes': ''})
        self.assertEqual(Location.objects.filter(embarcation=self.emb).count(), 1)

    def test_quick_rental_blocked_if_already_rented(self):
        now = timezone.now()
        Location.objects.create(
            embarcation=self.emb, gestionnaire=self.gestionnaire,
            heure_debut=now, heure_fin=now + timedelta(hours=1)
        )
        self.client.post(f'/gestionnaire/louer/{self.emb.pk}/', {'notes': ''})
        # Must still be only 1 location
        self.assertEqual(Location.objects.filter(embarcation=self.emb).count(), 1)


class RetourUndoTest(TestCase):
    """Annulation d'un retour validé par erreur (annuler_retour)."""

    def setUp(self):
        p = Ponton.objects.create(nom='P1', ordre=1)
        self.emb = Embarcation.objects.create(nom='K1', type_embarcation='kayak', ponton=p)
        self.gestionnaire = User.objects.create_user('gest', password='pass')
        UserProfile.objects.update_or_create(
            user=self.gestionnaire, defaults={'role': 'gestionnaire'}
        )
        self.client = Client()
        self.client.force_login(self.gestionnaire, backend=MODEL_BACKEND)
        now = timezone.now()
        self.loc = Location.objects.create(
            embarcation=self.emb, gestionnaire=self.gestionnaire, statut='sortie',
            heure_debut=now - timedelta(minutes=30), heure_fin=now + timedelta(minutes=30),
        )

    def _retour(self):
        return self.client.post(f'/gestionnaire/retour/{self.emb.pk}/', HTTP_HX_REQUEST='true')

    def _annuler(self, **extra):
        return self.client.post(f'/gestionnaire/retour/annuler/{self.loc.pk}/', **extra)

    def test_retour_announces_undo_url(self):
        resp = self._retour()
        self.loc.refresh_from_db()
        self.assertIsNotNone(self.loc.returned_at)
        self.assertIn(f'/gestionnaire/retour/annuler/{self.loc.pk}/', resp['HX-Trigger'])

    def test_undo_restores_active_rental(self):
        heure_fin = self.loc.heure_fin
        self._retour()
        self._annuler()
        self.loc.refresh_from_db()
        self.assertIsNone(self.loc.returned_at)
        self.assertEqual(self.loc.heure_fin, heure_fin)   # heure prévue intacte
        self.assertEqual(self.emb.location_en_cours(), self.loc)

    def test_undo_refused_after_window(self):
        returned = timezone.now() - timedelta(minutes=5)
        Location.objects.filter(pk=self.loc.pk).update(returned_at=returned)
        resp = self._annuler(HTTP_HX_REQUEST='true')
        self.loc.refresh_from_db()
        self.assertEqual(self.loc.returned_at, returned)
        self.assertIn('appToast', resp['HX-Trigger'])

    def test_undo_refused_if_rented_again(self):
        self._retour()
        self.client.post(f'/gestionnaire/louer/{self.emb.pk}/', {'notes': ''})
        self._annuler()
        self.loc.refresh_from_db()
        self.assertIsNotNone(self.loc.returned_at)
        # Une seule location active sur l'embarcation
        self.assertEqual(
            Location.objects.filter(embarcation=self.emb, returned_at__isnull=True).count(), 1
        )

    def test_undo_blocked_for_visiteur(self):
        self._retour()
        visiteur = User.objects.create_user('v1', password='pass')
        client = Client()
        client.force_login(visiteur, backend=MODEL_BACKEND)
        resp = client.post(f'/gestionnaire/retour/annuler/{self.loc.pk}/')
        self.assertRedirects(resp, '/planning/')
        self.loc.refresh_from_db()
        self.assertIsNotNone(self.loc.returned_at)


class HealthTest(TestCase):
    def test_health_is_public_and_ok(self):
        r = Client().get('/health')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, b'ok')
