from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from pontons.models import Ponton, Embarcation, Location, UserProfile


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
        })
        self.assertFalse(form.is_valid())

    def test_no_overlap_allowed(self):
        from pontons.forms import LocationForm
        form = LocationForm(data={
            'embarcation': self.emb.pk,
            'heure_debut': (self.now_local + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M'),
            'heure_fin':   (self.now_local + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M'),
        })
        self.assertTrue(form.is_valid())


class RoleAccessTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.visiteur = User.objects.create_user('v1', password='pass')
        # Signal auto-creates profile with default role='visiteur' — nothing extra needed

    def test_gestionnaire_view_blocked_for_visiteur(self):
        self.client.login(username='v1', password='pass')
        resp = self.client.get('/gestionnaire/')
        self.assertRedirects(resp, '/planning/')

    def test_admin_view_blocked_for_visiteur(self):
        self.client.login(username='v1', password='pass')
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
        self.client.login(username='gest', password='pass')

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
