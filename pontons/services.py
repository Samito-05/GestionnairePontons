from datetime import datetime, time, timedelta

from django.db.models import Q
from django.utils import timezone

from .models import Ponton, Location


def _text_color(hex_color):
    """Return #000 or #fff for maximum contrast against a hex background."""
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return '#000000' if luminance > 0.5 else '#ffffff'


def build_planning_data(date_cible=None, force_window_start=None):
    """Construit le planning avec positionnement CSS.

    Fenêtre GLISSANTE de 24h : maintenant ±12h (traverse minuit).
    Pour une autre date que aujourd'hui : centrée sur 13h ce jour-là.
    Passer force_window_start (datetime aware) pour préserver la fenêtre
    d'une page déjà chargée (évite le décalage visuel sur swap HTMX).

    Retourne (marks, planning, window_start, window_end, grid_span_minutes).
    """
    now = timezone.now()
    today = timezone.localdate()

    # ── 1. Fenêtre glissante, alignée sur l'heure pleine ─────────────────
    if force_window_start is not None:
        window_start = timezone.localtime(force_window_start).replace(
            minute=0, second=0, microsecond=0)
    else:
        if date_cible is None or date_cible == today:
            center = timezone.localtime(now)
        else:
            center = timezone.make_aware(datetime.combine(date_cible, time(13, 0)))
        window_start = center.replace(minute=0, second=0, microsecond=0) - timedelta(hours=12)
    window_end = window_start + timedelta(hours=24)

    GRID_SPAN = 24 * 60  # minutes

    def _offset_min(dt):
        """Minutes depuis le début de fenêtre (peut sortir de [0, 1440])."""
        return (dt - window_start).total_seconds() / 60

    # ── 2. Locations chevauchant la fenêtre ──────────────────────────────
    all_locs = Location.objects.filter(
        heure_debut__lt=window_end,
    ).filter(
        Q(heure_fin__gt=window_start) |
        Q(returned_at__gt=window_start) |
        Q(statut='sortie', returned_at__isnull=True)
    ).select_related('embarcation', 'gestionnaire')

    # ── 3. Graduations : heures + demi-heures, séparateur de jour à minuit ─
    marks = []
    for i in range(25):
        t = timezone.localtime(window_start + timedelta(hours=i))
        pct = i / 24 * 100
        is_midnight = (t.hour == 0)
        marks.append({
            'label':       f'{t.hour}h',
            'date_label':  t.strftime('%d/%m'),
            'pct':         f'{pct:.4f}',
            'is_hour':     True,
            'is_midnight': is_midnight,
            # Mobile : label toutes les 2h ; minuit toujours visible
            'show_mobile': (i % 2 == 0) or is_midnight,
        })
        if i < 24:
            half_pct = (i + 0.5) / 24 * 100
            marks.append({'label': '', 'date_label': '', 'pct': f'{half_pct:.4f}',
                          'is_hour': False, 'is_midnight': False, 'show_mobile': False})

    # ── 4. Construire le planning par ponton/embarcation ─────────────────
    pontons = Ponton.objects.filter(actif=True).prefetch_related('embarcations')

    loc_by_emb = {}
    for loc in all_locs:
        loc_by_emb.setdefault(loc.embarcation_id, []).append(loc)

    planning = []
    for ponton in pontons:
        rows = []
        for emb in ponton.embarcations.filter(actif=True):
            blocks = []
            is_rented_now = False
            retour_time   = None
            overtime      = False
            overtime_min  = 0
            current_loc   = None
            for loc in sorted(loc_by_emb.get(emb.id, []), key=lambda l: l.heure_debut):
                ld = timezone.localtime(loc.heure_debut)
                # Retour anticipé : le bloc s'arrête au retour réel
                fin_effective = loc.heure_fin
                if loc.statut == 'sortie' and loc.returned_at and loc.returned_at < loc.heure_fin:
                    fin_effective = loc.returned_at
                lf = timezone.localtime(fin_effective)

                # reservee: actif toute la journée locale tant que non sortie/retournée
                # sortie: actif tant que non retournée (dépassement inclus)
                is_active = loc.returned_at is None and (
                    (loc.statut == 'reservee' and ld.date() == today) or
                    (loc.statut == 'sortie' and loc.heure_debut <= now)
                )
                if is_active:
                    is_rented_now = True
                    retour_time   = lf.strftime('%H:%M') if loc.statut == 'sortie' else None
                    current_loc   = loc
                    if loc.is_overtime():
                        overtime     = True
                        overtime_min = loc.overtime_minutes

                is_reserved = loc.statut == 'reservee'

                start_min = max(_offset_min(loc.heure_debut), 0)
                end_min   = min(_offset_min(fin_effective), GRID_SPAN)
                # Resa gestionnaire active : la bande court jusqu'à la fin de fenêtre,
                # même si son heure_fin nominale est déjà sortie de la fenêtre
                if is_reserved and not loc.is_manual and is_active:
                    end_min = GRID_SPAN

                if end_min > start_min:
                    left_pct = start_min / GRID_SPAN * 100
                    if is_reserved and not loc.is_manual:
                        width_pct = 100.0 - left_pct
                    else:
                        width_pct = (end_min - start_min) / GRID_SPAN * 100

                    blocks.append({
                        'loc':         loc,
                        'left_pct':    f'{left_pct:.4f}',
                        'width_pct':   f'{width_pct:.4f}',
                        'color':       emb.couleur,
                        'text_color':  _text_color(emb.couleur),
                        'label':       f"{ld.strftime('%H:%M')}–{lf.strftime('%H:%M')}",
                        'is_reserved': is_reserved,
                        'is_overtime': False,
                    })

                # ── Segment de dépassement (sortie hors délai) ──────────────
                ot_end_dt = None
                if loc.statut == 'sortie':
                    if loc.returned_at is None and now > loc.heure_fin:
                        ot_end_dt = now                 # dépassement en cours
                    elif loc.returned_at and loc.returned_at > loc.heure_fin:
                        ot_end_dt = loc.returned_at     # retour tardif (historique)
                if ot_end_dt:
                    ot_start = max(_offset_min(loc.heure_fin), 0)
                    ot_end   = min(_offset_min(ot_end_dt), GRID_SPAN)
                    if ot_end > ot_start:
                        ot_left  = ot_start / GRID_SPAN * 100
                        ot_width = (ot_end - ot_start) / GRID_SPAN * 100
                        ot_mins  = int((ot_end_dt - loc.heure_fin).total_seconds() / 60)
                        blocks.append({
                            'loc':         loc,
                            'left_pct':    f'{ot_left:.4f}',
                            'width_pct':   f'{ot_width:.4f}',
                            'color':       '',
                            'text_color':  '',
                            'label':       f"Dépassement +{ot_mins} min",
                            'is_reserved': False,
                            'is_overtime': True,
                        })
            rows.append({
                'embarcation':          emb,
                'blocks':               blocks,
                'est_louee_maintenant': is_rented_now,
                'retour':               retour_time,
                'overtime':             overtime,
                'overtime_min':         overtime_min,
                'statut':               current_loc.statut if current_loc else None,
                'location_pk':          current_loc.pk if current_loc else None,
            })
        planning.append({'ponton': ponton, 'rows': rows})

    return marks, planning, window_start, window_end, GRID_SPAN
