from functools import wraps

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.views import redirect_to_login
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Prefetch, Q
from datetime import timedelta, date, datetime

from .models import Ponton, Embarcation, Location, UserProfile
from .forms import (
    PontonForm, EmbarcationForm,
    LocationForm, UserCreateForm, UserProfileForm,
)
from .services import build_planning_data
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
    """Décorateur qui vérifie le rôle minimum.

    Pour les requêtes HTMX, renvoie un header HX-Redirect au lieu d'un 302 :
    sinon htmx injecterait la page de login dans la tuile ciblée.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if request.headers.get('HX-Request'):
                    response = HttpResponse(status=401)
                    response['HX-Redirect'] = f"{settings.LOGIN_URL}?next={request.path}"
                    return response
                return redirect_to_login(request.get_full_path())
            role = get_user_role(request.user)
            if role not in roles and not request.user.is_superuser:
                if request.headers.get('HX-Request'):
                    response = HttpResponse(status=403)
                    response['HX-Redirect'] = '/planning/'
                    return response
                messages.error(request, "Accès refusé : droits insuffisants.")
                return redirect('planning')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


# Cibles autorisées pour le paramètre POST "next" (noms d'URL uniquement —
# jamais d'URL brute, pour bloquer les open redirects).
_ALLOWED_NEXT = {'gestionnaire', 'planning'}


def _safe_next(request):
    nxt = request.POST.get('next', 'gestionnaire')
    return nxt if nxt in _ALLOWED_NEXT else 'gestionnaire'


def _build_tile_item(embarcation):
    """Build item dict for gestionnaire tile partial (used by HTMX responses)."""
    loc = embarcation.location_en_cours()
    return {
        'embarcation': embarcation,
        'statut':      loc.statut if loc else None,
        'location':    loc,
        'retour':      timezone.localtime(loc.heure_fin).strftime('%H:%M') if (loc and loc.statut == 'sortie') else None,
        'overtime':    loc.is_overtime() if loc else False,
        'overtime_min': loc.overtime_minutes if loc else 0,
        'ticket_time': timezone.localtime(loc.created_at).strftime('%H:%M')
                       if (loc and loc.statut == 'reservee') else None,
    }


def _tile_response(request, embarcation):
    """Return rendered tile HTML for an HTMX swap."""
    item = _build_tile_item(embarcation)
    html = render_to_string('pontons/_gestionnaire_tile.html', {'item': item}, request=request)
    return HttpResponse(html)


def _build_planning_row(embarcation):
    """Build row dict for planning page partial (summary + mob tile)."""
    loc = embarcation.location_en_cours()
    return {
        'embarcation': embarcation,
        'blocks': [],
        'est_louee_maintenant': loc is not None,
        'retour': timezone.localtime(loc.heure_fin).strftime('%H:%M') if (loc and loc.statut == 'sortie') else None,
        'overtime': loc.is_overtime() if loc else False,
        'overtime_min': loc.overtime_minutes if loc else 0,
        'statut': loc.statut if loc else None,
        'location_pk': loc.pk if loc else None,
    }


def _planning_htmx_response(request, embarcation, partial):
    """Return full row/tile HTML (with real blocks) for HTMX swap.

    Reads window_start from the request so the partial uses the same
    rolling window as the already-rendered page (prevents visual offset).
    """
    ws = request.POST.get('window_start') or request.GET.get('window_start')
    force_ws = None
    if ws:
        try:
            force_ws = datetime.fromisoformat(ws)
            if timezone.is_naive(force_ws):
                force_ws = timezone.make_aware(force_ws)
        except ValueError:
            force_ws = None

    marks, planning_data, _, _, _ = build_planning_data(None, force_ws)

    row = None
    for ponton_data in planning_data:
        for r in ponton_data['rows']:
            if r['embarcation'].pk == embarcation.pk:
                row = r
                break
        if row:
            break

    if row is None:
        row = _build_planning_row(embarcation)

    ctx = {'row': row, 'marks': marks}
    if partial == 'planning_tl':
        html = render_to_string('pontons/_planning_tl_row.html', ctx, request=request)
    elif partial == 'planning_mob_tl':
        html = render_to_string('pontons/_planning_mob_tl_row.html', ctx, request=request)
    else:
        html = render_to_string('pontons/_planning_mob_tile.html', ctx, request=request)
    return HttpResponse(html)


def planning_row_partial(request, pk):
    """GET endpoint for HTMX polling — refreshes a single embarcation row."""
    embarcation = get_object_or_404(Embarcation, pk=pk, actif=True)
    partial = request.GET.get('partial', 'planning_tl')
    return _planning_htmx_response(request, embarcation, partial)


# ─── Vue Planning ──────────────────────────────────────────────────────────────

def planning(request):
    date_str = request.GET.get('date')
    try:
        date_cible = date.fromisoformat(date_str) if date_str else timezone.localdate()
    except ValueError:
        date_cible = timezone.localdate()

    marks, planning_data, window_start, window_end, grid_span = build_planning_data(date_cible)

    return render(request, 'pontons/planning.html', {
        'marks':            marks,
        'planning_data':    planning_data,
        'date_cible':       date_cible,
        'date_prev':        date_cible - timedelta(days=1),
        'date_next':        date_cible + timedelta(days=1),
        'now':              timezone.localtime(timezone.now()),
        'window_start':     window_start,
        'window_end':       window_end,
        'window_start_iso': window_start.isoformat(),
        'window_start_ms':  int(window_start.timestamp() * 1000),
        'grid_span':        grid_span,
    })


# ─── Vue Gestionnaire ──────────────────────────────────────────────────────────

@require_role('admin', 'gestionnaire')
def gestionnaire(request):
    now = timezone.now()
    active_locs_qs = Location.objects.filter(
        Q(statut='reservee', heure_debut__date=timezone.localdate(), returned_at__isnull=True) |
        Q(statut='sortie', heure_debut__lte=now, returned_at__isnull=True)
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
                'statut': loc.statut if loc else 'libre',
                'location': loc,
                'retour': timezone.localtime(loc.heure_fin).strftime('%H:%M') if (loc and loc.statut == 'sortie') else None,
                'overtime': loc.is_overtime() if loc else False,
                'overtime_min': loc.overtime_minutes if loc else 0,
                'ticket_time': timezone.localtime(loc.created_at).strftime('%H:%M') if (loc and loc.statut == 'reservee') else None,
            })
        embarcations_status.append({'ponton': ponton, 'embarcations': embs})

    return render(request, 'pontons/gestionnaire.html', {
        'embarcations_status': embarcations_status,
        'now': timezone.localtime(now),
    })


@require_role('admin', 'gestionnaire')
@require_POST
def louer_embarcation(request, pk):
    now = timezone.now()
    with transaction.atomic():
        embarcation = get_object_or_404(
            Embarcation.objects.select_for_update(), pk=pk, actif=True
        )
        overlap = Location.objects.filter(
            Q(embarcation=embarcation, statut='reservee', heure_debut__date=timezone.localdate(), returned_at__isnull=True) |
            Q(embarcation=embarcation, statut='sortie', heure_debut__lte=now, returned_at__isnull=True)
        )
        next_url = _safe_next(request)
        if overlap.exists():
            if request.headers.get('HX-Request'):
                partial = request.POST.get('_htmx_partial', 'gestionnaire')
                if partial in ('planning_mob', 'planning_tl', 'planning_mob_tl'):
                    return _planning_htmx_response(request, embarcation, partial)
                return _tile_response(request, embarcation)
            messages.warning(request, f"{embarcation.nom} est déjà en location sur ce créneau.")
            return redirect(next_url)
        Location.objects.create(
            embarcation=embarcation,
            gestionnaire=request.user,
            heure_debut=now,
            heure_fin=now + timedelta(hours=1),
            statut='reservee',
            notes=request.POST.get('notes', ''),
        )
    if request.headers.get('HX-Request'):
        partial = request.POST.get('_htmx_partial', 'gestionnaire')
        if partial in ('planning_mob', 'planning_tl', 'planning_mob_tl'):
            return _planning_htmx_response(request, embarcation, partial)
        return _tile_response(request, embarcation)
    return redirect(next_url)


@require_role('admin', 'gestionnaire')
@require_POST
def sortir_embarcation(request, pk):
    next_url = _safe_next(request)
    with transaction.atomic():
        embarcation = get_object_or_404(Embarcation.objects.select_for_update(), pk=pk)
        loc = embarcation.location_en_cours()
        if loc and loc.statut == 'reservee':
            now = timezone.now()
            duration = loc.heure_fin - loc.heure_debut
            loc.heure_debut = now
            loc.heure_fin = now + duration
            loc.statut = 'sortie'
            loc.save()
    if request.headers.get('HX-Request'):
        partial = request.POST.get('_htmx_partial', 'gestionnaire')
        if partial in ('planning_mob', 'planning_tl', 'planning_mob_tl'):
            return _planning_htmx_response(request, embarcation, partial)
        return _tile_response(request, embarcation)
    return redirect(next_url)


@require_role('admin', 'gestionnaire')
@require_POST
def retour_embarcation(request, pk):
    next_url = _safe_next(request)
    with transaction.atomic():
        embarcation = get_object_or_404(Embarcation.objects.select_for_update(), pk=pk)
        loc = embarcation.location_en_cours()
        if loc:
            # Retour effectif : marque returned_at. On ne touche PAS heure_fin
            # pour préserver le bloc prévu + le dépassement éventuel dans l'historique.
            loc.returned_at = timezone.now()
            loc.save()
    if request.headers.get('HX-Request'):
        partial = request.POST.get('_htmx_partial', 'gestionnaire')
        if partial in ('planning_mob', 'planning_tl', 'planning_mob_tl'):
            return _planning_htmx_response(request, embarcation, partial)
        return _tile_response(request, embarcation)
    return redirect(next_url)


# ─── Vues Admin ───────────────────────────────────────────────────────────────

@require_role('admin')
def admin_dashboard(request):
    return render(request, 'pontons/admin/dashboard.html', {
        'nb_pontons': Ponton.objects.count(),
        'nb_embarcations': Embarcation.objects.filter(actif=True).count(),
        'nb_locations_today': Location.objects.filter(heure_debut__date=timezone.localdate()).count(),
        'nb_users': User.objects.count(),
    })


# — Pontons —

@require_role('admin')
def admin_pontons(request):
    pontons = Ponton.objects.annotate(nb_embarcations=Count('embarcations'))
    return render(request, 'pontons/admin/pontons.html', {'pontons': pontons})


@require_role('admin')
def admin_ponton_new(request):
    form = PontonForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('admin_pontons')
    return render(request, 'pontons/admin/ponton_form.html', {'form': form, 'titre': 'Nouveau ponton'})


@require_role('admin')
def admin_ponton_edit(request, pk):
    ponton = get_object_or_404(Ponton, pk=pk)
    form = PontonForm(request.POST or None, instance=ponton)
    if form.is_valid():
        form.save()
        return redirect('admin_pontons')
    return render(request, 'pontons/admin/ponton_form.html', {'form': form, 'titre': 'Modifier le ponton'})


@require_role('admin')
@require_POST
def admin_ponton_delete(request, pk):
    ponton = get_object_or_404(Ponton, pk=pk)
    ponton.delete()
    return redirect('admin_pontons')


# — Embarcations —

@require_role('admin')
def admin_embarcations(request):
    now = timezone.now()
    embarcations = Embarcation.objects.select_related('ponton').annotate(
        nb_locations=Count('locations'),
        est_louee_now=Exists(
            Location.objects.filter(
                Q(embarcation=OuterRef('pk'), statut='reservee', heure_debut__date=timezone.localdate(), returned_at__isnull=True) |
                Q(embarcation=OuterRef('pk'), statut='sortie', heure_debut__lte=now, returned_at__isnull=True)
            )
        )
    )
    return render(request, 'pontons/admin/embarcations.html', {'embarcations': embarcations})


@require_role('admin')
def admin_embarcation_new(request):
    form = EmbarcationForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('admin_embarcations')
    return render(request, 'pontons/admin/embarcation_form.html', {'form': form, 'titre': 'Nouvelle embarcation'})


@require_role('admin')
def admin_embarcation_edit(request, pk):
    emb = get_object_or_404(Embarcation, pk=pk)
    form = EmbarcationForm(request.POST or None, instance=emb)
    if form.is_valid():
        form.save()
        return redirect('admin_embarcations')
    return render(request, 'pontons/admin/embarcation_form.html', {'form': form, 'titre': "Modifier l'embarcation"})


@require_role('admin')
@require_POST
def admin_embarcation_delete(request, pk):
    emb = get_object_or_404(Embarcation, pk=pk)
    emb.delete()
    return redirect('admin_embarcations')


# — Locations —

@require_role('admin')
def admin_locations(request):
    date_str = request.GET.get('date')
    try:
        date_cible = date.fromisoformat(date_str) if date_str else timezone.localdate()
    except ValueError:
        date_cible = timezone.localdate()

    locations = Location.objects.filter(
        heure_debut__date=date_cible
    ).select_related('embarcation', 'gestionnaire', 'embarcation__ponton').order_by('heure_debut')

    return render(request, 'pontons/admin/locations.html', {
        'locations': locations,
        'date_cible': date_cible,
        'date_prev': date_cible - timedelta(days=1),
        'date_next': date_cible + timedelta(days=1),
    })


@require_role('admin')
def admin_location_new(request):
    form = LocationForm(request.POST or None, initial={'statut': 'sortie'})
    if form.is_valid():
        loc = form.save(commit=False)
        loc.gestionnaire = request.user
        loc.is_manual = True
        loc.save()
        return redirect('admin_locations')
    return render(request, 'pontons/admin/location_form.html', {'form': form, 'titre': 'Nouvelle location'})


@require_role('admin')
def admin_location_edit(request, pk):
    loc = get_object_or_404(Location, pk=pk)
    form = LocationForm(request.POST or None, instance=loc)
    if form.is_valid():
        form.save()
        return redirect('admin_locations')
    return render(request, 'pontons/admin/location_form.html', {'form': form, 'titre': 'Modifier la location'})


@require_role('admin')
@require_POST
def admin_location_delete(request, pk):
    loc = get_object_or_404(Location, pk=pk)
    loc.delete()
    return redirect('admin_locations')


# — Utilisateurs —

@require_role('admin')
def admin_users(request):
    users = User.objects.select_related('profile').all().order_by('username')
    return render(request, 'pontons/admin/users.html', {'users': users})


@require_role('admin')
def admin_user_new(request):
    form = UserCreateForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('admin_users')
    return render(request, 'pontons/admin/user_form.html', {'form': form, 'titre': 'Nouvel utilisateur'})


@require_role('admin')
def admin_user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    profile, _ = UserProfile.objects.get_or_create(user=user)
    form = UserProfileForm(request.POST or None, instance=profile)
    if form.is_valid():
        form.save()
        return redirect('admin_users')
    return render(request, 'pontons/admin/user_form.html', {
        'form': form, 'titre': f'Modifier {user.username}', 'edit_user': user,
    })


@require_role('admin')
@require_POST
def admin_user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, 'Vous ne pouvez pas supprimer votre propre compte.')
        return redirect('admin_users')
    user.delete()
    return redirect('admin_users')


# ─── API JSON (pour rafraîchissement live) ────────────────────────────────────

def api_status(request):
    now = timezone.now()
    current_locs = {
        loc.embarcation_id: loc
        for loc in Location.objects.filter(
            Q(statut='reservee', heure_debut__date=timezone.localdate(), returned_at__isnull=True) |
            Q(statut='sortie', heure_debut__lte=now, returned_at__isnull=True)
        )
    }
    data = []
    for emb in Embarcation.objects.filter(actif=True).select_related('ponton'):
        loc = current_locs.get(emb.id)
        data.append({
            'id': emb.id,
            'nom': emb.nom,
            'ponton': emb.ponton.nom,
            'louee': loc is not None,
            'statut': loc.statut if loc else 'libre',
            'retour': timezone.localtime(loc.heure_fin).strftime('%H:%M') if (loc and loc.statut == 'sortie') else None,
            'overtime': loc.is_overtime() if loc else False,
        })
    return JsonResponse({'status': data, 'now': timezone.localtime(now).strftime('%H:%M:%S')})
