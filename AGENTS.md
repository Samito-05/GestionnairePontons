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
- **WhiteNoise** for static file serving (`CompressedManifestStaticFilesStorage`)
- **HTMX** for partial page swaps (planning rows + gestionnaire tiles refresh without full reload)
- **Custom CSS** in `static/css/base.css`. Form widgets use Bulma-style class names (`input`, `select`, `textarea`) but there is **no Bulma stylesheet loaded** — styling comes from `base.css`. Do not assume Bulma is available.
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
templates/       base.html, pontons/, pontons/admin/, registration/
static/          css/base.css, icons/, manifest.json, sw.js
data/            db.sqlite3 (gitignored)
```

## Domain model

- **Ponton** → has many **Embarcation** → has many **Location**.
- **Location** statuses: `reservee` (reserved) and `sortie` (out on the water).
  - `reservee`: active all day, **no time expiry** — valid until the boat is taken out or returned.
  - `sortie`: active until **actually returned** — tracked by `returned_at` (null = still out). `heure_fin` is only the *scheduled* end; passing it does **not** free the boat. A `sortie` past `heure_fin` with `returned_at IS NULL` is **overtime** (`is_overtime()` / `overtime_minutes`), shown as a striped red segment on the timeline and a red "Retard +N min" state on the tiles.
  - "active now" everywhere = `returned_at IS NULL` (+ `heure_debut__lte=now` for sortie). This clause is duplicated across `models`, `views` (gestionnaire, louer, admin_embarcations, api_status) and `services` — keep them in sync.
- **Return** (`retour_embarcation`) sets `returned_at = now` and leaves `heure_fin` untouched, so the overtime segment stays visible in history. Do not overwrite `heure_fin` on return.
- `Location.is_manual` distinguishes admin-created rentals (fixed `heure_fin`, exact block) from gestionnaire quick-rentals (block extends to end of grid on the planning).
- **UserProfile** holds `role`; auto-created for every new `User` via a `post_save` signal. Never assume a profile is missing — `get_or_create` where needed.

The state machine for a quick rental: **libre → reservee** (louer) **→ sortie** (sortir) **→ libre** (retour). Admin can create a `Location` directly in any state.

## Conventions — follow these

- **Roles**: gate views with the `@require_role('admin', ...)` decorator from `views.py`. Read the current role via `get_user_role(user)` (view) or the `role` template variable (injected by `context_processors.user_role`). Do not re-invent role checks.
- **Timezone**: `USE_TZ=True`, `TIME_ZONE='Europe/Paris'`. Store/compare in UTC (`timezone.now()`); convert for display with `timezone.localtime(...)`. `datetime-local` form input is naive → `LocationForm.clean()` makes it aware. Preserve this pattern when touching datetimes.
- **Overlap protection**: rental collisions are rejected in two places — `LocationForm.clean()` (admin forms) and `louer_embarcation` (uses `select_for_update()` inside `transaction.atomic()` for the quick-rent race). Keep both.
- **Planning grid**: window is computed dynamically from the day's rentals in `services.build_planning_data`, falling back to **13h–20h**. HTMX partials pass `grid_start`/`grid_end` back so a swapped row keeps the same bounds as the loaded page (avoids visual offset). Don't hardcode the window.
- **HTMX partials**: views branch on `request.headers.get('HX-Request')` and a `_htmx_partial` POST field (`gestionnaire`, `planning_mob`, `planning_tl`, `planning_mob_tl`). Partial templates are the `_`-prefixed files under `templates/pontons/`.
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

`pontons/tests.py` covers: rental overlap rejection, role-based access redirects, the `UserProfile` auto-create signal, and the atomic quick-rental race guard. **Run `python manage.py test` after any change to models, forms, views, or the role logic**, and add cases when you extend that behavior.

## Configuration & secrets

- Settings read from env via `python-dotenv`. `DJANGO_SECRET_KEY` is **required** (no default — app crashes if missing). `DJANGO_DEBUG` defaults to `False`. `DJANGO_ALLOWED_HOSTS` is comma-separated.
- Local: copy `.env.example` → `.env`. Prod: `.env.production` (from `.env.production.example`) — **never commit either**.
- Production hardening (HSTS, secure cookies, proxy SSL header) activates automatically when `DEBUG=False`. `SECURE_SSL_REDIRECT` is intentionally **off** — Cloudflare Tunnel terminates TLS and forwards HTTP to `127.0.0.1:8000`; do not re-enable Django's redirect.

## Deployment

Docker Compose runs two services: `web` (gunicorn, bound to `127.0.0.1:8000`) and `tunnel` (cloudflared). `deploy.sh` pulls the latest `main` from GitHub, copies source over the running checkout (preserving `.env.production`), rebuilds, and runs migrations. SQLite and media live in named volumes.

## Demo accounts

`admin/admin123` (superuser) · `gestionnaire1/gest123` · `visiteur1/visit123` — dev only, created by `init_demo`.

## Do / Don't

- **Do** keep changes inside the `pontons` app unless there's a clear reason to touch `config`.
- **Do** preserve the two-status rental semantics and the tz-aware handling — they're subtle.
- **Don't** commit `.env*`, `data/db.sqlite3`, or anything under `venv/` `.venv/`.
- **Don't** assume Bulma CSS — style with `static/css/base.css`.
- **Don't** run `init_demo` against a production database (it refuses when `DEBUG=False`).
