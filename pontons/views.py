from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from datetime import timedelta, datetime, date
import json

from .models import Ponton, Embarcation, Location, UserProfile
from .forms import (
    LocationRapideForm, PontonForm, EmbarcationForm,
    LocationForm, UserCreateForm, UserProfileForm,
)
from django.contrib.auth.models import User


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_user_role(user):
    if user.is_superuser:
        return 'admin'
    try:
        return user.profile.role
    except UserProfile.DoesNotExist:
        return 'visiteur'


def require_role(*roles):
    """Décorateur qui vérifie le rôle minimum."""
    def decorator(view_func):
        @login_required
        def _wrapped(request, *args, **kwargs):
            role = get_user_role(request.user)
            if role not in roles and not request.user.is_superuser:
                messages.error(request, "Accès refusé : droits insuffisants.")
                return redirect('planning')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def build_planning_data(date_cible):
    """Construit la structure de données pour le planning d'une journée."""
    # Créneaux : 13h00 → 20h00 par tranches de 30 min → 14 slots
    slots = []
    for i in range(14):
        h = 13 + i // 2
        m = 30 if i % 2 else 0
        slots.append(f"{h:02d}:{m:02d}")

    debut_jour = timezone.make_aware(datetime.combine(date_cible, datetime.min.time().replace(hour=13)))
    fin_jour = timezone.make_aware(datetime.combine(date_cible, datetime.min.time().replace(hour=20)))

    pontons = Ponton.objects.filter(actif=True).prefetch_related('embarcations')
    locations_jour = Location.objects.filter(
        heure_debut__lt=fin_jour,
        heure_fin__gt=debut_jour,
    ).select_related('embarcation', 'gestionnaire')

    # Indexer les locations par embarcation
    loc_by_emb = {}
    for loc in locations_jour:
        loc_by_emb.setdefault(loc.embarcation_id, []).append(loc)

    planning = []
    for ponton in pontons:
        rows = []
        for emb in ponton.embarcations.filter(actif=True):
            cells = [None] * 14  # 14 slots de 30 min
            skip_until = -1
            locs = sorted(loc_by_emb.get(emb.id, []), key=lambda l: l.heure_debut)

            for loc in locs:
                # Convertir heure_debut en slot index (0-13)
                local_debut = timezone.localtime(loc.heure_debut)
                local_fin = timezone.localtime(loc.heure_fin)
                slot_start = (local_debut.hour - 13) * 2 + (1 if local_debut.minute >= 30 else 0)
                slot_end = (local_fin.hour - 13) * 2 + (1 if local_fin.minute > 0 else 0)
                slot_start = max(0, min(slot_start, 13))
                slot_end = max(0, min(slot_end, 14))

                if slot_start < 14:
                    span = max(1, slot_end - slot_start)
                    cells[slot_start] = {
                        'loc': loc,
                        'span': span,
                        'color': emb.couleur,
                    }
                    for s in range(slot_start + 1, min(slot_start + span, 14)):
                        cells[s] = 'skip'

            rows.append({'embarcation': emb, 'cells': cells})
        planning.append({'ponton': ponton, 'rows': rows})

    return slots, planning


# ─── Vue Planning ──────────────────────────────────────────────────────────────

def planning(request):
    date_str = request.GET.get('date')
    try:
        date_cible = date.fromisoformat(date_str) if date_str else date.today()
    except ValueError:
        date_cible = date.today()

    slots, planning_data = build_planning_data(date_cible)
    role = get_user_role(request.user) if request.user.is_authenticated else 'visiteur'

    return render(request, 'pontons/planning.html', {
        'slots': slots,
        'planning_data': planning_data,
        'date_cible': date_cible,
        'date_prev': date_cible - timedelta(days=1),
        'date_next': date_cible + timedelta(days=1),
        'now': timezone.localtime(timezone.now()),
        'role': role,
    })


# ─── Vue Gestionnaire ──────────────────────────────────────────────────────────

@require_role('admin', 'gestionnaire')
def gestionnaire(request):
    pontons = Ponton.objects.filter(actif=True).prefetch_related('embarcations')
    now = timezone.now()

    embarcations_status = []
    for ponton in pontons:
        embs = []
        for emb in ponton.embarcations.filter(actif=True):
            loc = emb.location_en_cours()
            embs.append({
                'embarcation': emb,
                'louee': loc is not None,
                'location': loc,
                'retour': timezone.localtime(loc.heure_fin).strftime('%H:%M') if loc else None,
            })
        embarcations_status.append({'ponton': ponton, 'embarcations': embs})

    return render(request, 'pontons/gestionnaire.html', {
        'embarcations_status': embarcations_status,
        'now': timezone.localtime(now),
        'role': get_user_role(request.user),
    })


@require_role('admin', 'gestionnaire')
@require_POST
def louer_embarcation(request, pk):
    embarcation = get_object_or_404(Embarcation, pk=pk, actif=True)
    now = timezone.now()

    if embarcation.est_louee_maintenant():
        messages.warning(request, f"{embarcation.nom} est déjà en location.")
        return redirect('gestionnaire')

    notes = request.POST.get('notes', '')
    Location.objects.create(
        embarcation=embarcation,
        gestionnaire=request.user,
        heure_debut=now,
        heure_fin=now + timedelta(hours=1),
        notes=notes,
    )
    retour = timezone.localtime(now + timedelta(hours=1)).strftime('%H:%M')
    messages.success(request, f"{embarcation.nom} louée jusqu'à {retour}.")
    return redirect('gestionnaire')


@require_role('admin', 'gestionnaire')
@require_POST
def retour_embarcation(request, pk):
    embarcation = get_object_or_404(Embarcation, pk=pk)
    loc = embarcation.location_en_cours()
    if loc:
        loc.heure_fin = timezone.now()
        loc.save()
        messages.success(request, f"{embarcation.nom} est de retour.")
    else:
        messages.info(request, f"{embarcation.nom} n'est pas en location.")
    return redirect('gestionnaire')


# ─── Vues Admin ───────────────────────────────────────────────────────────────

@require_role('admin')
def admin_dashboard(request):
    return render(request, 'pontons/admin/dashboard.html', {
        'nb_pontons': Ponton.objects.count(),
        'nb_embarcations': Embarcation.objects.filter(actif=True).count(),
        'nb_locations_today': Location.objects.filter(heure_debut__date=date.today()).count(),
        'nb_users': User.objects.count(),
        'role': 'admin',
    })


# — Pontons —

@require_role('admin')
def admin_pontons(request):
    pontons = Ponton.objects.all()
    return render(request, 'pontons/admin/pontons.html', {'pontons': pontons, 'role': 'admin'})


@require_role('admin')
def admin_ponton_new(request):
    form = PontonForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Ponton créé.')
        return redirect('admin_pontons')
    return render(request, 'pontons/admin/ponton_form.html', {'form': form, 'titre': 'Nouveau ponton', 'role': 'admin'})


@require_role('admin')
def admin_ponton_edit(request, pk):
    ponton = get_object_or_404(Ponton, pk=pk)
    form = PontonForm(request.POST or None, instance=ponton)
    if form.is_valid():
        form.save()
        messages.success(request, 'Ponton mis à jour.')
        return redirect('admin_pontons')
    return render(request, 'pontons/admin/ponton_form.html', {'form': form, 'titre': 'Modifier le ponton', 'role': 'admin'})


@require_role('admin')
@require_POST
def admin_ponton_delete(request, pk):
    ponton = get_object_or_404(Ponton, pk=pk)
    ponton.delete()
    messages.success(request, 'Ponton supprimé.')
    return redirect('admin_pontons')


# — Embarcations —

@require_role('admin')
def admin_embarcations(request):
    embarcations = Embarcation.objects.select_related('ponton').all()
    return render(request, 'pontons/admin/embarcations.html', {'embarcations': embarcations, 'role': 'admin'})


@require_role('admin')
def admin_embarcation_new(request):
    form = EmbarcationForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Embarcation créée.')
        return redirect('admin_embarcations')
    return render(request, 'pontons/admin/embarcation_form.html', {'form': form, 'titre': 'Nouvelle embarcation', 'role': 'admin'})


@require_role('admin')
def admin_embarcation_edit(request, pk):
    emb = get_object_or_404(Embarcation, pk=pk)
    form = EmbarcationForm(request.POST or None, instance=emb)
    if form.is_valid():
        form.save()
        messages.success(request, 'Embarcation mise à jour.')
        return redirect('admin_embarcations')
    return render(request, 'pontons/admin/embarcation_form.html', {'form': form, 'titre': 'Modifier l\'embarcation', 'role': 'admin'})


@require_role('admin')
@require_POST
def admin_embarcation_delete(request, pk):
    emb = get_object_or_404(Embarcation, pk=pk)
    emb.delete()
    messages.success(request, 'Embarcation supprimée.')
    return redirect('admin_embarcations')


# — Locations —

@require_role('admin')
def admin_locations(request):
    date_str = request.GET.get('date')
    try:
        date_cible = date.fromisoformat(date_str) if date_str else date.today()
    except ValueError:
        date_cible = date.today()

    locations = Location.objects.filter(
        heure_debut__date=date_cible
    ).select_related('embarcation', 'gestionnaire', 'embarcation__ponton').order_by('heure_debut')

    return render(request, 'pontons/admin/locations.html', {
        'locations': locations,
        'date_cible': date_cible,
        'date_prev': date_cible - timedelta(days=1),
        'date_next': date_cible + timedelta(days=1),
        'role': 'admin',
    })


@require_role('admin')
def admin_location_new(request):
    form = LocationForm(request.POST or None)
    if form.is_valid():
        loc = form.save(commit=False)
        loc.gestionnaire = request.user
        loc.save()
        messages.success(request, 'Location créée.')
        return redirect('admin_locations')
    return render(request, 'pontons/admin/location_form.html', {'form': form, 'titre': 'Nouvelle location', 'role': 'admin'})


@require_role('admin')
def admin_location_edit(request, pk):
    loc = get_object_or_404(Location, pk=pk)
    form = LocationForm(request.POST or None, instance=loc)
    if form.is_valid():
        form.save()
        messages.success(request, 'Location mise à jour.')
        return redirect('admin_locations')
    return render(request, 'pontons/admin/location_form.html', {'form': form, 'titre': 'Modifier la location', 'role': 'admin'})


@require_role('admin')
@require_POST
def admin_location_delete(request, pk):
    loc = get_object_or_404(Location, pk=pk)
    loc.delete()
    messages.success(request, 'Location supprimée.')
    return redirect('admin_locations')


# — Utilisateurs —

@require_role('admin')
def admin_users(request):
    users = User.objects.select_related('profile').all().order_by('username')
    return render(request, 'pontons/admin/users.html', {'users': users, 'role': 'admin'})


@require_role('admin')
def admin_user_new(request):
    form = UserCreateForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Utilisateur créé.')
        return redirect('admin_users')
    return render(request, 'pontons/admin/user_form.html', {'form': form, 'titre': 'Nouvel utilisateur', 'role': 'admin'})


@require_role('admin')
def admin_user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    profile, _ = UserProfile.objects.get_or_create(user=user)
    form = UserProfileForm(request.POST or None, instance=profile)
    if form.is_valid():
        form.save()
        messages.success(request, 'Rôle mis à jour.')
        return redirect('admin_users')
    return render(request, 'pontons/admin/user_form.html', {
        'form': form, 'titre': f'Modifier {user.username}', 'edit_user': user, 'role': 'admin'
    })


@require_role('admin')
@require_POST
def admin_user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, 'Vous ne pouvez pas supprimer votre propre compte.')
        return redirect('admin_users')
    user.delete()
    messages.success(request, 'Utilisateur supprimé.')
    return redirect('admin_users')


# ─── API JSON (pour rafraîchissement live) ────────────────────────────────────

def api_status(request):
    now = timezone.now()
    data = []
    for emb in Embarcation.objects.filter(actif=True).select_related('ponton'):
        loc = emb.location_en_cours()
        data.append({
            'id': emb.id,
            'nom': emb.nom,
            'ponton': emb.ponton.nom,
            'louee': loc is not None,
            'retour': timezone.localtime(loc.heure_fin).strftime('%H:%M') if loc else None,
        })
    return JsonResponse({'status': data, 'now': timezone.localtime(now).strftime('%H:%M:%S')})
