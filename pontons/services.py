from django.utils import timezone

from .models import Ponton, Location


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
    # ── 1. Récupérer TOUTES les locations du jour (sans filtre horaire) ──
    all_locs_today = Location.objects.filter(
        heure_debut__date=date_cible,
    ).select_related('embarcation', 'gestionnaire')

    # ── 2. Calculer la fenêtre temporelle dynamique ──────────────────────
    # grid_end_h : minimum 20h fixe, s'étend si locations dépassent 20h
    if all_locs_today.exists():
        local_starts = [timezone.localtime(l.heure_debut) for l in all_locs_today]
        local_ends   = [timezone.localtime(l.heure_fin)   for l in all_locs_today]
        min_h = min(t.hour for t in local_starts)
        max_h = max(t.hour + (1 if t.minute > 0 else 0) for t in local_ends)
        grid_start_h = max(6,  min_h - 1)
        grid_end_h   = min(23, max(max_h + 1, 20))
    else:
        grid_start_h = 13
        grid_end_h   = 20

    GRID_START = grid_start_h * 60
    GRID_END   = grid_end_h   * 60
    GRID_SPAN  = GRID_END - GRID_START

    # ── 3. Graduations : heures pleines + demi-heures ────────────────────
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
            current_loc   = None
            for loc in sorted(loc_by_emb.get(emb.id, []), key=lambda l: l.heure_debut):
                ld = timezone.localtime(loc.heure_debut)
                lf = timezone.localtime(loc.heure_fin)

                if loc.heure_debut <= now < loc.heure_fin:
                    is_rented_now = True
                    retour_time   = lf.strftime('%H:%M')
                    current_loc   = loc

                start_min = max(ld.hour * 60 + ld.minute, GRID_START)
                end_min   = min(lf.hour * 60 + lf.minute, GRID_END)
                if end_min <= start_min:
                    continue

                left_pct  = (start_min - GRID_START) / GRID_SPAN * 100
                width_pct = (end_min - start_min)    / GRID_SPAN * 100

                # Blocs "vente" (réservé, pas encore sorti) → gris
                is_vente = getattr(loc, 'statut', 'sortie') == 'reservee'
                block_color = '#6e8394' if is_vente else emb.couleur
                blocks.append({
                    'loc':        loc,
                    'left_pct':   f'{left_pct:.4f}',
                    'width_pct':  f'{width_pct:.4f}',
                    'color':      block_color,
                    'text_color': _text_color(block_color),
                    'label':      f"{ld.strftime('%H:%M')}–{lf.strftime('%H:%M')}",
                })
            rows.append({
                'embarcation':          emb,
                'blocks':               blocks,
                'est_louee_maintenant': is_rented_now,
                'retour':               retour_time,
                'statut':               current_loc.statut if current_loc else None,
                'location_pk':          current_loc.pk if current_loc else None,
            })
        planning.append({'ponton': ponton, 'rows': rows})

    return marks, planning, grid_start_h, grid_end_h, GRID_SPAN
