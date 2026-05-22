# 🚤 Gestionnaire Pontons

Application web de gestion de locations d'embarcations (pédalos, kayaks, canoës, SUP…) avec planning visuel, interface gestionnaire et administration complète.

> Installable comme application mobile (PWA) — fonctionne sur Android, iOS et desktop.

---

## Stack

| Composant | Technologie |
|---|---|
| Backend | Django 5.2 (Python 3.12) |
| Base de données | SQLite (dev) — remplaçable par PostgreSQL/MySQL |
| CSS | Thème maritime custom (CSS variables) + Font Awesome 6 |
| Serveur de fichiers statiques | WhiteNoise + CompressedManifest |
| Serveur WSGI | Gunicorn (production) |
| Mobile | PWA (manifest + service worker) |
| Déploiement | Docker + Cloudflare Tunnel |

---

## Développement local

### Prérequis

- Python 3.10+
- pip

### Installation

```bash
git clone https://github.com/Samito-05/GestionnairePontons.git
cd GestionnairePontons

# Copier la config locale
cp .env.example .env
# Éditer .env si besoin (DEBUG=True, clé générée automatiquement)
```

#### Windows — script tout-en-un

```powershell
# Lance : venv → dépendances → migrations → données démo → serveur
.\startup.ps1

# Options utiles
.\startup.ps1 -NoRunServer     # Prépare sans lancer le serveur
.\startup.ps1 -SkipInstall     # Ignore pip install
.\startup.ps1 -SkipDemo        # Ignore les données de démo
.\startup.ps1 -ResetDatabase   # Recrée la base SQLite depuis zéro
.\startup.ps1 -Port 8080       # Change le port
```

#### Manuel (Linux/macOS/Windows)

```bash
python -m venv venv
source venv/bin/activate          # Linux/macOS
# venv\Scripts\activate           # Windows

pip install -r requirements.txt
python manage.py migrate
python manage.py init_demo        # Données de démo (optionnel)
python manage.py runserver
```

Ouvrir : [http://127.0.0.1:8000](http://127.0.0.1:8000)

### Comptes de démo

> ⚠️ Ces comptes n'existent qu'après `init_demo`. **Ne jamais utiliser en production.**

| Identifiant | Mot de passe | Rôle |
|---|---|---|
| `admin` | `admin123` | Superadmin |
| `gestionnaire1` | `gest123` | Gestionnaire |
| `visiteur1` | `visit123` | Visiteur (lecture seule) |

---

## Production — Docker + Cloudflare Tunnel

### Architecture

```
Navigateur → Cloudflare (HTTPS) → Tunnel chiffré → QNAP/serveur (Docker, port 8000 local)
```

Cloudflare gère le HTTPS. Le serveur n'est jamais directement exposé à Internet.

### Prérequis

- Docker + Docker Compose sur le serveur (ou NAS avec Container Station)
- Compte Cloudflare avec un domaine
- Accès SSH au serveur

### 1 — Récupérer le code

```bash
# Option A : git
git clone https://github.com/Samito-05/GestionnairePontons.git
cd GestionnairePontons

# Option B : zip (si git non disponible)
wget -O pontons.zip https://github.com/Samito-05/GestionnairePontons/archive/refs/heads/main.zip
unzip pontons.zip && mv GestionnairePontons-main GestionnairePontons
cd GestionnairePontons
```

### 2 — Créer le fichier de configuration production

```bash
cp .env.production.example .env.production
```

Éditer `.env.production` :

```env
DJANGO_SECRET_KEY=<générer avec la commande ci-dessous>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=pontons.tondomaine.com
TUNNEL_TOKEN=<token Cloudflare — étape 4>
```

Générer une clé secrète :

```bash
# Sur le serveur (si Python dispo)
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Sur Windows (dans le dossier du projet)
python manage.py shell -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

> **Note :** Si la clé contient des `$`, les échapper en `$$` dans le fichier `.env.production`
> (Docker Compose interprète `$` comme une variable shell).

### 3 — Lancer l'application

```bash
docker compose up -d --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

Vérifier :

```bash
docker compose ps               # web: Up, tunnel: Up
curl -I http://127.0.0.1:8000   # HTTP/1.1 302 Found
```

### 4 — Configurer le tunnel Cloudflare

1. Aller sur [one.dash.cloudflare.com](https://one.dash.cloudflare.com) → **Networks → Tunnels**
2. **Create a tunnel** → **Cloudflared** → nommer `gestionnaire-pontons` → **Save**
3. Copier le token affiché, le coller dans `.env.production` (`TUNNEL_TOKEN=...`)
4. Dans **Public Hostnames → Add** :

| Champ | Valeur |
|---|---|
| Subdomain | `pontons` |
| Domain | `tondomaine.com` |
| Service Type | `HTTP` |
| URL | `web:8000` |

5. Relancer le tunnel :

```bash
docker compose up -d tunnel
```

### Mise à jour

```bash
# Télécharger la nouvelle version
git pull   # ou re-télécharger le ZIP

# Reconstruire et redémarrer
docker compose up -d --build
docker compose exec web python manage.py migrate   # si nouvelles migrations
```

### Commandes utiles

```bash
docker compose logs -f                    # Logs en temps réel
docker compose restart web                # Redémarrer l'appli sans rebuild
docker compose down                       # Arrêter tout
docker compose exec web python manage.py shell   # Shell Django

# Sauvegarde base de données
docker compose exec web python manage.py dumpdata > backup_$(date +%Y%m%d).json
```

### Dépannage

| Symptôme | Cause | Solution |
|---|---|---|
| 502 Bad gateway | Conteneur `web` arrêté | `docker compose up -d` |
| Tunnel inactif | Token manquant ou mauvais | Vérifier `TUNNEL_TOKEN` dans `.env.production` |
| 500 / erreur Django | Erreur applicative | `docker compose logs web` |
| DisallowedHost | Domaine absent de `ALLOWED_HOSTS` | Ajouter dans `.env.production` + `docker compose restart web` |
| Médias perdus au rebuild | Volume non persisté | Vérifier que `media_data` est défini dans `docker-compose.yml` |

---

## Rôles et permissions

| Rôle | Capacités |
|---|---|
| **Visiteur** | Consulter le planning (lecture seule), naviguer entre les dates |
| **Gestionnaire** | + Louer une embarcation, marquer le retour anticipé |
| **Admin** | + CRUD pontons, embarcations, locations, utilisateurs |

---

## Structure du projet

```
GestionnairePontons/
├── config/
│   ├── settings.py          # Config Django (secrets via env vars)
│   ├── urls.py
│   └── wsgi.py
├── pontons/
│   ├── models.py            # Ponton, Embarcation, Location, UserProfile
│   ├── views.py
│   ├── forms.py
│   ├── urls.py
│   └── management/commands/
│       └── init_demo.py     # Données de démo
├── templates/
│   ├── base.html
│   ├── registration/login.html
│   └── pontons/
│       ├── planning.html
│       ├── gestionnaire.html
│       └── admin/
├── static/
│   ├── manifest.json        # PWA
│   ├── sw.js                # Service worker (cache-first static, jamais HTML)
│   └── icons/
├── Dockerfile
├── docker-compose.yml
├── .env.example             # Template config dev (commité, sans secrets)
├── .env.production.example  # Template config prod (commité, sans secrets)
├── .env                     # Config dev réelle (gitignored)
├── .env.production          # Config prod réelle (gitignored, sur le serveur)
├── startup.ps1              # Script démarrage Windows (dev)
├── startup.bat
└── requirements.txt
```

---

## Modèle de données

```
Ponton
  └── Embarcation (type, couleur, ordre)
        └── Location (heure_debut, heure_fin, gestionnaire, notes)

User
  └── UserProfile (role: admin | gestionnaire | visiteur)
```

---

## URLs principales

| URL | Accès |
|---|---|
| `/` | Redirige vers planning |
| `/planning/` | Public |
| `/planning/?date=YYYY-MM-DD` | Public |
| `/gestionnaire/` | Gestionnaire+ |
| `/gestion/` | Admin |
| `/api/status/` | Public (JSON temps réel) |
| `/admin/` | Superuser Django |

---

## Licence

Projet libre d'utilisation. Adapter à vos besoins.
