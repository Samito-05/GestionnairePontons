from django.utils import timezone

from .models import Ponton, Location


def _text_color(hex_color):
    """Return #000 or #fff for maximum contrast against a hex background."""
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return '#000000' if luminance > 0.5 else '#ffffff'


def build_planning_data(date_cible, force_grid_start=None, force_grid_end=None):
    """Construit le planning avec positionnement CSS.

    La fenêtre temporelle (grid_start_h → grid_end_h) est calculée
    dynamiquement depuis les locations du jour, avec un fallback 13h–20h.
    Passer force_grid_start/force_grid_end pour préserver les bornes
    d'une page déjà chargée (évite le décalage visuel sur swap HTMX).
    """
    now = timezone.now()

    # ── 1. Récupérer TOUTES les locations du jour (sans filtre horaire) ──
    all_locs_today = Location.objects.filter(
        heure_debut__date=date_cible,
    ).select_related('embarcation', 'gestionnaire')

    def _effective_end(loc):
        """Fin réelle pour le calcul de fenêtre : étend au dépassement live
        (sortie non retournée, fin dépassée) ou au retour tardif historique."""
        if loc.statut == 'sortie' and loc.returned_at is None and now > loc.heure_fin:
            return now
        if loc.returned_at and loc.returned_at > loc.heure_fin:
            return loc.returned_at
        return loc.heure_fin

    # ── 2. Calculer la fenêtre temporelle dynamique ──────────────────────
    if force_grid_start is not None and force_grid_end is not None:
        grid_start_h = int(force_grid_start)
        grid_end_h   = int(force_grid_end)
    elif all_locs_today.exists():
        local_starts = [timezone.localtime(l.heure_debut) for l in all_locs_today]
        local_ends   = [timezone.localtime(_effective_end(l)) for l in all_locs_today]
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
            overtime      = False
            overtime_min  = 0
            current_loc   = None
            for loc in sorted(loc_by_emb.get(emb.id, []), key=lambda l: l.heure_debut):
                ld = timezone.localtime(loc.heure_debut)
                lf = timezone.localtime(loc.heure_fin)

                # reservee: actif toute la journée (pas d'expiration horaire)
                # sortie: actif tant que non retournée (dépassement inclus)
                is_active = loc.returned_at is None and (
                    loc.statut == 'reservee' or
                    (loc.statut == 'sortie' and loc.heure_debut <= now)
                )
                if is_active:
                    is_rented_now = True
                    retour_time   = lf.strftime('%H:%M') if loc.statut == 'sortie' else None
                    current_loc   = loc
                    if loc.is_overtime():
                        overtime     = True
                        overtime_min = loc.overtime_minutes

                start_min = max(ld.hour * 60 + ld.minute, GRID_START)
                end_min   = min(lf.hour * 60 + lf.minute, GRID_END)

                is_reserved = loc.statut == 'reservee'
                if end_min > start_min:
                    left_pct = (start_min - GRID_START) / GRID_SPAN * 100
                    # Resa via gestionnaire (is_manual=False) : bloc jusqu'à fin de grille
                    # Resa manuelle (is_manual=True) : bloc exact heure_debut–heure_fin
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
                        ot_end_dt = now                # dépassement en cours
                    elif loc.returned_at and loc.returned_at > loc.heure_fin:
                        ot_end_dt = loc.returned_at     # retour tardif (historique)
                if ot_end_dt:
                    ote = timezone.localtime(ot_end_dt)
                    ot_start = max(lf.hour * 60 + lf.minute, GRID_START)
                    ot_end   = min(ote.hour * 60 + ote.minute, GRID_END)
                    if ot_end > ot_start:
                        ot_left  = (ot_start - GRID_START) / GRID_SPAN * 100
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

    return marks, planning, grid_start_h, grid_end_h, GRID_SPAN
