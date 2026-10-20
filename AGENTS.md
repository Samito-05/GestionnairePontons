# AGENTS.md

Guidance for AI coding agents working in this repository. Read this before making changes.

## Project overview

**Gestionnaire Pontons** is a Django web app + PWA for managing hourly rentals of small watercraft (pedalos, kayaks, canoes, SUPs, barques) across pontoons ("pontons"). Branded "La Plage — L'Isle-Adam". UI language is **French**; keep all user-facing strings in French.

Three access levels, each with its own area:

| Role | Access | Entry URL |
|------|--------|-----------|
| `admin` | Full CRUD on pontoons, boats, rentals, users | `/gestion/` |
| `gestionnaire` | Rent / take out / return a boat (quick ops) | `/gestionnaire/` |
| `visiteur` | Read-only planning | `/planning/` |

`admin` implies `gestionnaire` rights. Superusers are always treated as `admin`.

## Tech stack

- **Django 5.2**, Python 3.12
- **SQLite** database at `data/db.sqlite3`
- **WhiteNoise** for static file serving (`CompressedManifestStaticFilesStorage`, declared in `STORAGES` — the old `STATICFILES_STORAGE` setting is ignored since Django 5.1). Hashed names need `collectstatic` (done in the Docker build); `manage.py test` switches to the plain storage via `TESTING` in settings.
- **HTMX** for partial page swaps (planning rows + gestionnaire tiles refresh without full reload). Vendored at `static/js/htmx.min.js` (1.9.12) — no CDN.
- **Custom CSS** in `static/css/base.css` — the single stylesheet (design tokens, components, every page; light + dark via `[data-theme]`). Form widgets use Bulma-style class names (`input`, `select`, `textarea`) but there is **no Bulma stylesheet loaded** — styling comes from `base.css`. Do not assume Bulma is available.
- **Shared JS** in `static/js/app.js` (theme, toasts, confirm dialog, HTMX error toasts, clock, tile countdowns, state counters). Page-specific JS stays inline in the page template.
- **Fonts** self-hosted in `static/fonts/` (Fraunces = display, Figtree = UI; OFL). RGPD: **no third-party CDN** for fonts, scripts or styles.
- **Icons**: inline SVG sprite `templates/_icons.html`, used as `<svg class="icon"><use href="#i-name"/></svg>`. No icon font.
- **PWA**: `static/manifest.json` + `static/sw.js`
- **Gunicorn** in production, containerized via Docker + Cloudflare Tunnel
- `gunicorn`, `python-dotenv` runtime deps; `django-extensions`, `Pillow` dev-only

## Layout

```
config/          Django project (settings, urls, wsgi, asgi)
pontons/         Main app — the only project app
  models.py      Ponton, Embarcation, Location, UserProfile
  views.py       Planning, gestionnaire ops, admin CRUD, HTMX partials, JSON API
  forms.py       ModelForms with overlap validation + tz handling
  services.py    build_planning_data() — planning grid computation
  admin.py       Django admin registrations
  context_processors.py   injects `role` into every template
  urls.py        app routes
  management/commands/  init_demo, peuple_bdd
templates/       base.html, _icons.html, pontons/, pontons/admin/, registration/
static/          css/base.css, js/ (app.js, htmx.min.js), fonts/, icons/, manifest.json, sw.js
data/            db.sqlite3 (gitignored)
```

## Domain model

- **Ponton** → has many **Embarcation** → has many **Location**.
- **Location** statuses: `reservee` (reserved) and `sortie` (out on the water).
  - `reservee`: active all day, **no time expiry** — valid until the boat is taken out or returned.
  - `sortie`: active until **actually returned** — tracked by `returned_at` (null = still out). `heure_fin` is only the *scheduled* end; passing it does **not** free the boat. A `sortie` past `heure_fin` with `returned_at IS NULL` is **overtime** (`is_overtime()` / `overtime_minutes`), shown as a striped red segment on the timeline and a red "Retard +N min" state on the tiles.
  - "active now" everywhere = `returned_at IS NULL` (+ `heure_debut__lte=now` for sortie). This clause is duplicated across `models`, `views` (gestionnaire, louer, admin_embarcations, api_status) and `services` — keep them in sync.
- **Return** (`retour_embarcation`) sets `returned_at = now` and leaves `heure_fin` untouched, so the overtime segment stays visible in history. Do not overwrite `heure_fin` on return.
- **Undo return** (`annuler_retour`, POST `/gestionnaire/retour/annuler/<location pk>/`) clears `returned_at` again. Only within `RETOUR_UNDO_WINDOW` (60 s) and only if the boat has no active rental since — otherwise two rentals would be active on one boat. The return response advertises it through an `HX-Trigger: retourFait` header; `app.js` shows the "Annuler" toast.
- `Location.is_manual` distinguishes admin-created rentals (fixed `heure_fin`, exact block) from gestionnaire quick-rentals (block extends to end of grid on the planning).
- **UserProfile** holds `role`; auto-created for every new `User` via a `post_save` signal. Never assume a profile is missing — `get_or_create` where needed.

The state machine for a quick rental: **libre → reservee** (louer) **→ sortie** (sortir) **→ libre** (retour). Admin can create a `Location` directly in any state.

## Conventions — follow these

- **Roles**: gate views with the `@require_role('admin', ...)` decorator from `views.py`. Read the current role via `get_user_role(user)` (view) or the `role` template variable (injected by `context_processors.user_role`). Do not re-invent role checks.
- **Timezone**: `USE_TZ=True`, `TIME_ZONE='Europe/Paris'`. Store/compare in UTC (`timezone.now()`); convert for display with `timezone.localtime(...)`. `datetime-local` form input is naive → `LocationForm.clean()` makes it aware. Preserve this pattern when touching datetimes.
- **Overlap protection**: rental collisions are rejected in two places — `LocationForm.clean()` (admin forms) and `louer_embarcation` (uses `select_for_update()` inside `transaction.atomic()` for the quick-rent race). Keep both.
- **Planning grid**: window is computed dynamically from the day's rentals in `services.build_planning_data`, falling back to **13h–20h**. HTMX partials pass `grid_start`/`grid_end` back so a swapped row keeps the same bounds as the loaded page (avoids visual offset). Don't hardcode the window.
- **HTMX partials**: views branch on `request.headers.get('HX-Request')` and a `_htmx_partial` POST field (`gestionnaire`, `planning_mob`, `planning_tl`, `planning_mob_tl`). Partial templates are the `_`-prefixed files under `templates/pontons/`.
- **UI components** (all in `base.css`): boat tiles are `.tile` + `.tile--libre|reservee|sortie` (+ `.is-late`) with `data-statut` — shared by `_gestionnaire_tile.html` and `_planning_mob_tile.html`; the state counters/filters and the mobile "retards" badge are computed client-side from those attributes, so keep them on any new tile markup. A `sortie` tile carries `data-end` (scheduled end, ms epoch) for the live countdown.
- **Live refresh without reload**: `/gestionnaire/` re-fetches itself via HTMX (`hx-select="#board-sections"`) when the operator is idle; `/planning/` uses `softRefresh()` (fetch + swap of `#tl-inner`, `#mob-tl-inner`, `#mob-grid`), and falls back to a full reload only when the 24h window has shifted. Keep those ids stable.
- **Feedback**: Django `messages` render as floating toasts (`success`/`warning`/`error`/`info`); in-page boxes use `.notice`. Destructive forms use `data-confirm="Titre"` (+ `data-confirm-detail`) — handled by the `<dialog>` in `base.html`, never `confirm()`.
- **Admin forms** render through `pontons/admin/_form_fields.html`; list tables add `data-label` on each `<td>` (they collapse into cards on mobile).
- **Navigation**: top bar on desktop, bottom tab bar on mobile (gestionnaire/admin only); the admin sidebar becomes a scrollable tab strip on mobile.
- **French UI**: user-facing text, `messages`, verbose names, choices labels — all French.
- **Custom admin area** (`/gestion/`) is separate from Django's built-in admin (`/admin/`). Both exist. New management UI generally goes under `/gestion/`.

## Commands

```bash
python manage.py runserver          # dev server (from repo root)
python manage.py migrate            # apply migrations
python manage.py makemigrations     # after model changes
python manage.py test               # run test suite (pontons/tests.py)
python manage.py init_demo          # seed demo data — DEBUG=True only, refuses in prod
python manage.py peuple_bdd         # populate DB (see command source)
python manage.py collectstatic      # gather static for prod
```

Windows note: this repo lives on Windows. A `.venv/` and a `venv/` both exist; activate the intended one (`venv\Scripts\activate` or `.venv\Scripts\activate`). `startup.bat` / `startup.ps1` are convenience launchers.

## Tests

`pontons/tests.py` covers: rental overlap rejection, role-based access redirects, the `UserProfile` auto-create signal, the atomic quick-rental race guard, and undo-return (restore, expiry, re-rented, role gate). Log test users in with `force_login(user, backend=MODEL_BACKEND)` — `client.login()` fails under django-axes (no request object). **Run `python manage.py test` after any change to models, forms, views, or the role logic**, and add cases when you extend that behavior.

## Configuration & secrets

- Settings read from env via `python-dotenv`. `DJANGO_SECRET_KEY` is **required** (no default — app crashes if missing). `DJANGO_DEBUG` defaults to `False`. `DJANGO_ALLOWED_HOSTS` is comma-separated.
- Local: copy `.env.example` → `.env`. Prod: `.env.production` (from `.env.production.example`) — **never commit either**.
- Production hardening (HSTS, secure cookies, proxy SSL header) activates automatically when `DEBUG=False`. `SECURE_SSL_REDIRECT` is intentionally **off** — Cloudflare Tunnel terminates TLS and forwards HTTP to the container; do not re-enable Django's redirect.

## Deployment

Production runs from **Samito-05/nas-stack**, which builds this repo's `Dockerfile` next to the other projects behind one Cloudflare Tunnel, and handles pulls, backups and health waits. This repo only provides the image: migrations run at container start (`CMD`), `/health` is the healthcheck probe (public, `SELECT 1`), and `.dockerignore` keeps `.env*`, `data/` and `.git` out of the image. `docker-compose.yml` is a local test of the production image only (`127.0.0.1:8000`). SQLite lives in a named volume at `/app/data`. Keep `localhost` in `DJANGO_ALLOWED_HOSTS` for the healthcheck.

## Demo accounts

`admin/admin123` (superuser) · `gestionnaire1/gest123` · `visiteur1/visit123` — dev only, created by `init_demo`.

## Do / Don't

- **Do** keep changes inside the `pontons` app unless there's a clear reason to touch `config`.
- **Do** preserve the two-status rental semantics and the tz-aware handling — they're subtle.
- **Don't** commit `.env*`, `data/db.sqlite3`, or anything under `venv/` `.venv/`.
- **Don't** assume Bulma CSS — style with `static/css/base.css`.
- **Don't** run `init_demo` against a production database (it refuses when `DEBUG=False`).
