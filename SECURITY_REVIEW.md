# Security Review — GestionnairePontons

**Branch:** main | **Date:** 2026-05-22 | **Reviewer:** Claude Security Review

---

## Summary

| Severity | Count |
|---|---|
| Critical | 1 |
| High | 1 |
| Medium | 0 |
| Low | 0 |

---

## Vuln 1: Hardcoded Insecure SECRET_KEY — `config/settings.py:5`

* **Severity:** Critical
* **Category:** secrets_management / authentication_bypass
* **Confidence:** 9/10

**Description:**
`SECRET_KEY` is hardcoded with Django's own `'django-insecure-'` warning prefix and committed to the git repository. Django uses this key to cryptographically sign session cookies, CSRF tokens, and password-reset tokens.

```python
SECRET_KEY = 'django-insecure-=in4&s4g4v=*8v*gf81^v89(8a@xh@n3*5vu!k%_=-^=ovmb#c'
```

**Exploit Scenario:**
Anyone with read access to the git repo (or who has seen a git log, clone, or CI artifact) possesses the signing key. They can:
1. Forge a valid session cookie → instant authentication as any user including superuser
2. Forge CSRF tokens → bypass CSRF protection on all POST endpoints
3. Forge password-reset links → account takeover without email access

**Recommendation:**
```python
# config/settings.py
import os
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']  # Required, no default
```

Generate a new key (treat the committed key as permanently compromised):
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## Vuln 2: `DEBUG=True` in Production — `config/settings.py:7`

* **Severity:** High
* **Category:** data_exposure / information_disclosure
* **Confidence:** 9/10

**Description:**
`DEBUG = True` is hardcoded with no environment override. The app is deployed via `python manage.py runserver 0.0.0.0:8000` (LAN-accessible per commit `df88d3b`). On any unhandled exception, Django renders a full debug page to the client.

**Exploit Scenario:**
Attacker triggers any 500 error (malformed request, edge-case input, nonexistent URL variant). Django serves a debug page containing:
- Full Python stack trace with local variable values at each frame
- Absolute filesystem paths exposing server layout
- Complete list of installed apps and middleware
- Subset of `settings` values (enough to map attack surface)
- All SQL queries executed during the request

This is active data exfiltration on demand, not theoretical.

**Recommendation:**
```python
# config/settings.py
import os
DEBUG = os.environ.get('DJANGO_DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '127.0.0.1').split(',')
```

Run production with `DJANGO_DEBUG` unset (defaults to `False`). Use gunicorn or uWSGI, not `runserver`.

---

## Pre-Deployment Checklist

| Item | Status | Fix |
|---|---|---|
| `SECRET_KEY` from env | ❌ | `os.environ['DJANGO_SECRET_KEY']` |
| `DEBUG=False` in prod | ❌ | `os.environ.get('DJANGO_DEBUG', 'False')` |
| `ALLOWED_HOSTS` restricted | ❌ | Set to actual hostname/IP |
| WSGI server (not `runserver`) | ❌ | gunicorn / uWSGI |
| HTTPS / HSTS | ⚠️ | `SECURE_SSL_REDIRECT=True`, `SECURE_HSTS_SECONDS=31536000` |
| `CSRF_COOKIE_SECURE=True` | ⚠️ | Requires HTTPS first |
| `SESSION_COOKIE_SECURE=True` | ⚠️ | Requires HTTPS first |

---

## Confirmed Safe

| Area | Status | Notes |
|---|---|---|
| CSRF tokens | ✅ | Present on all POST forms |
| SQL injection | ✅ | Django ORM used throughout, no raw queries |
| XSS | ✅ | Auto-escaping active, no `\|safe` misuse |
| Role-based access control | ✅ | All admin views protected by `@require_role` |
| IDOR | ✅ | `get_object_or_404` + role checks on all object lookups |
| `api_status` endpoint (unauthenticated) | ✅ | Intentional — feeds public planning page, no PII |
| `next` redirect on login | ✅ | Django `LoginView` validates with `url_has_allowed_host_and_scheme()` |
