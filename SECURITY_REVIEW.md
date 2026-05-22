# Security Review — GestionnairePontons

**Date:** 2026-05-22 | **Reviewer:** Claude Security Review | **Status:** ✅ Fixed

---

## Summary

| Severity | Count | Status |
|---|---|---|
| Critical | 1 | ✅ Fixed |
| High | 1 | ✅ Fixed |
| Medium | 0 | — |
| Low | 0 | — |

---

## Vuln 1: Hardcoded SECRET_KEY — `config/settings.py`

* **Severity:** Critical → **Fixed**
* **Category:** secrets_management / authentication_bypass
* **Confidence:** 9/10

**Description:**
`SECRET_KEY` was hardcoded with Django's `'django-insecure-'` prefix and committed to the repository. Django uses this key to sign session cookies, CSRF tokens, and password-reset tokens — possession of the key allows forging all three.

**Fix applied:**
```python
# config/settings.py
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']  # Required — crashes if missing
```

Key is now read from environment. A fresh key is generated for each deployment via `.env.production` (gitignored).

---

## Vuln 2: `DEBUG=True` in Production — `config/settings.py`

* **Severity:** High → **Fixed**
* **Category:** data_exposure / information_disclosure
* **Confidence:** 9/10

**Description:**
`DEBUG = True` was hardcoded. On any unhandled exception, Django renders a debug page exposing full stack traces, local variable values, file paths, and settings to the client.

**Fix applied:**
```python
DEBUG = os.environ.get('DJANGO_DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')
```

Production deployments default to `DEBUG=False`. `ALLOWED_HOSTS` is restricted to declared hosts only.

---

## Production hardening added

```python
if not DEBUG:
    SECURE_SSL_REDIRECT = False             # Cloudflare Tunnel handles TLS
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

---

## Confirmed Safe

| Area | Status | Notes |
|---|---|---|
| CSRF tokens | ✅ | Present on all POST forms |
| SQL injection | ✅ | Django ORM throughout, no raw queries |
| XSS | ✅ | Auto-escaping active, no `\|safe` misuse |
| Role-based access control | ✅ | All admin views protected by `@require_role` |
| IDOR | ✅ | `get_object_or_404` + role checks on all object lookups |
| `api/status/` endpoint | ✅ | Intentional public endpoint — subset of public planning data, no PII |
| `next` redirect on login | ✅ | Django `LoginView` validates with `url_has_allowed_host_and_scheme()` |
