from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Count, Exists, OuterRef, Prefetch
from datetime import timedelta, datetime, date

from .models import Ponton, Embarcation, Location, UserProfile
from .forms import (
    PontonForm, EmbarcationForm,
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


def _text_color(hex_color):
    """Return #000 or #fff for maximum contrast against a hex background."""
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return '#000000' if luminance > 0.5 else '#ffffff'


def build_planning_data(date_cible):
    """Construit le planning avec positionnement CSS.

    La fenêtre temporelle (grid_start_h → grid_end_h) est calculée
    dynamiquement depuis les locations du jour, avec un fallback 13h–20h.
    Ainsi une location créée à n'importe quelle heure reste visible.
    """
    from datetime import time as dtime

    # ── 1. Récupérer TOUTES les locations du jour (sans filtre horaire) ──
    all_locs_today = Location.objects.filter(
        heure_debut__date=date_cible,
    ).select_related('embarcation', 'gestionnaire')

    # ── 2. Calculer la fenêtre temporelle dynamique ──────────────────────
    if all_locs_today.exists():
        local_starts = [timezone.localtime(l.heure_debut) for l in all_locs_today]
        local_ends   = [timezone.localtime(l.heure_fin)   for l in all_locs_today]
        min_h = min(t.hour for t in local_starts)
        max_h = max(t.hour + (1 if t.minute > 0 else 0) for t in local_ends)
        # Padding d'1h de chaque côté, limites absolues 6h–23h, min 3h de large
        grid_start_h = max(6,  min_h - 1)
        grid_end_h   = min(23, max(max_h + 1, grid_start_h + 3))
    else:
        grid_start_h = 13
        grid_end_h   = 20

    GRID_START = grid_start_h * 60
    GRID_END   = grid_end_h   * 60
    GRID_SPAN  = GRID_END - GRID_START

    # ── 3. Graduations : heures pleines + demi-heures ────────────────────
    # Les pct sont des strings avec point décimal (locale fr-fr safe)
    marks = []
    step_mobile = max(1, round((grid_end_h - grid_start_h) / 4))
    for h in range(grid_start_h, grid_end_h + 1):
        pct = (h * 60 - GRID_START) / GRID_SPAN * 100
        show_mobile = ((h - grid_start_h) % step_mobile == 0) or (h == grid_end_h)
        marks.append({'label': f'{h}h', 'pct': f'{pct:.4f}',
                      'is_hour': True, 'show_mobile': show_mobile})
        if h < grid_end_h:
            half_pct = ((h * 60 + 30) - GRID_START) / GRID_SPAN * 100
            marks.append({'label': '', 'pct': f'{half_pct:.4f}',
                          'is_hour': False, 'show_mobile': False})

    # ── 4. Construire le planning par ponton/embarcation ─────────────────
    now = timezone.now()
    pontons = Ponton.objects.filter(actif=True).prefetch_related('embarcations')

    loc_by_emb = {}
    for loc in all_locs_today:
        loc_by_emb.setdefault(loc.embarcation_id, []).append(loc)

    planning = []
    for ponton in pontons:
        rows = []
        for emb in ponton.embarcations.filter(actif=True):
            blocks = []
            is_rented_now = False
            retour_time   = None
            for loc in sorted(loc_by_emb.get(emb.id, []), key=lambda l: l.heure_debut):
                ld = timezone.localtime(loc.heure_debut)
                lf = timezone.localtime(loc.heure_fin)

                if loc.heure_debut <= now < loc.heure_fin:
                    is_rented_now = True
                    retour_time   = lf.strftime('%H:%M')

                start_min = max(ld.hour * 60 + ld.minute, GRID_START)
                end_min   = min(lf.hour * 60 + lf.minute, GRID_END)
                if end_min <= start_min:
                    continue

                left_pct  = (start_min - GRID_START) / GRID_SPAN * 100
                width_pct = (end_min - start_min)    / GRID_SPAN * 100

                blocks.append({
                    'loc':        loc,
                    'left_pct':   f'{left_pct:.4f}',
                    'width_pct':  f'{width_pct:.4f}',
                    'color':      emb.couleur,
                    'text_color': _text_color(emb.couleur),
                    'label':      f"{ld.strftime('%H:%M')}–{lf.strftime('%H:%M')}",
                })
            rows.append({
                'embarcation':      emb,
                'blocks':           blocks,
                'est_louee_maintenant': is_rented_now,
                'retour':           retour_time,
            })
        planning.append({'ponton': ponton, 'rows': rows})

    return marks, planning, grid_start_h, grid_end_h, GRID_SPAN


# ─── Vue Planning ──────────────────────────────────────────────────────────────

def planning(request):
    date_str = request.GET.get('date')
    try:
        date_cible = date.fromisoformat(date_str) if date_str else date.today()
    except ValueError:
        date_cible = date.today()

    marks, planning_data, grid_start_h, grid_end_h, grid_span = build_planning_data(date_cible)
    role = get_user_role(request.user) if request.user.is_authenticated else 'visiteur'

    return render(request, 'pontons/planning.html', {
        'marks':         marks,
        'planning_data': planning_data,
        'date_cible':    date_cible,
        'date_prev':     date_cible - timedelta(days=1),
        'date_next':     date_cible + timedelta(days=1),
        'now':           timezone.localtime(timezone.now()),
        'role':          role,
        'grid_start_h':  grid_start_h,
        'grid_end_h':    grid_end_h,
        'grid_span':     grid_span,
    })


# ─── Vue Gestionnaire ──────────────────────────────────────────────────────────

@require_role('admin', 'gestionnaire')
def gestionnaire(request):
    now = timezone.now()
    active_locs_qs = Location.objects.filter(
        heure_debut__lte=now, heure_fin__gt=now
    ).select_related('gestionnaire')
    pontons = Ponton.objects.filter(actif=True).prefetch_related(
        Prefetch(
            'embarcations',
            queryset=Embarcation.objects.filter(actif=True).prefetch_related(
                Prefetch('locations', queryset=active_locs_qs, to_attr='locations_actives')
            ),
        )
    )

    embarcations_status = []
    for ponton in pontons:
        embs = []
        for emb in ponton.embarcations.all():
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
    pontons = Ponton.objects.annotate(nb_embarcations=Count('embarcations'))
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
    now = timezone.now()
    embarcations = Embarcation.objects.select_related('ponton').annotate(
        est_louee_now=Exists(
            Location.objects.filter(
                embarcation=OuterRef('pk'),
                heure_debut__lte=now,
                heure_fin__gt=now,
            )
        )
    )
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
    current_locs = {
        loc.embarcation_id: loc
        for loc in Location.objects.filter(heure_debut__lte=now, heure_fin__gt=now)
    }
    data = []
    for emb in Embarcation.objects.filter(actif=True).select_related('ponton'):
        loc = current_locs.get(emb.id)
        data.append({
            'id': emb.id,
            'nom': emb.nom,
            'ponton': emb.ponton.nom,
            'louee': loc is not None,
            'retour': timezone.localtime(loc.heure_fin).strftime('%H:%M') if loc else None,
        })
    return JsonResponse({'status': data, 'now': timezone.localtime(now).strftime('%H:%M:%S')})
