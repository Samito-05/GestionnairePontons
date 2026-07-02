# Gestionnaire Pontons

Application web de gestion de locations d'embarcations (pédalos, kayaks, canoës, barques, SUP) avec planning visuel, interface de gestion rapide et administration complète.

Installable comme application mobile (PWA) sur Android, iOS et desktop.

---

## Stack

| Composant | Version |
|---|---|
| Python | 3.12 |
| Django | 5.2 |
| Base de données | SQLite (dev) / remplaçable PostgreSQL ou MySQL |
| CSS | Thème maritime custom (CSS variables, sans framework) |
| Icônes | Font Awesome 6 (CDN) |
| Fichiers statiques | WhiteNoise 6.8 avec CompressedManifestStaticFilesStorage |
| WSGI | Gunicorn 23 |
| Anti brute-force | django-axes 7 (5 echecs → compte verrouille 15 min) |
| Variables d'environnement | python-dotenv 1.0 |
| Déploiement | Docker + Cloudflare Tunnel |
| PWA | manifest.json + Service Worker v3 (cache-first static, HTML jamais mis en cache) |

---

## Développement local

### Prérequis

- Python 3.10 ou supérieur
- pip

### Mise en place

```bash
git clone https://github.com/Samito-05/GestionnairePontons.git
cd GestionnairePontons

cp .env.example .env
# .env est prérempli pour le dev local — aucune modification requise
```

#### Windows — script tout-en-un

```powershell
# Lance dans l'ordre : venv, dependances pip, migrations, donnees demo, serveur
.\startup.ps1

# Options
.\startup.ps1 -NoRunServer    # Prepare l'environnement sans lancer le serveur
.\startup.ps1 -SkipInstall    # Ignore pip install (dependances deja presentes)
.\startup.ps1 -SkipDemo       # Ignore le chargement des donnees de demonstration
.\startup.ps1 -ResetDatabase  # Supprime et recrée la base SQLite
.\startup.ps1 -Port 8080      # Change le port (defaut : 8000)
```

#### Autre OS

```bash
python -m venv venv
source venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py init_demo    # Optionnel — charge les donnees de demonstration
python manage.py runserver
```

Ouvrir : http://127.0.0.1:8000

### Commandes de developpement courantes

```bash
# Apres modification des modeles
python manage.py makemigrations && python manage.py migrate

# Reinitialiser les donnees de demonstration
python manage.py flush --no-input && python manage.py init_demo

# Verification systeme Django
python manage.py check
```

### Comptes de demonstration

Disponibles apres `init_demo`. Ne pas utiliser en production.

| Identifiant | Mot de passe | Role |
|---|---|---|
| `admin` | `admin123` | Superadmin |
| `gestionnaire1` | `gest123` | Gestionnaire |
| `visiteur1` | `visit123` | Visiteur |

---

## Production

### Architecture

```
Navigateur  -->  Cloudflare (HTTPS/TLS)  -->  Tunnel chiffre  -->  Serveur Docker (port 8000, local uniquement)
```

Cloudflare gere le HTTPS et le certificat. Le serveur n'est jamais expose directement a Internet — aucun port a ouvrir sur la box ou le pare-feu.

### Prérequis

- Serveur ou NAS avec Docker et Docker Compose (QNAP Container Station supporte)
- Compte Cloudflare avec un domaine
- Acces SSH au serveur

### 1. Recuperer le code

```bash
# Avec git installe sur le NAS
git clone https://github.com/Samito-05/GestionnairePontons.git
cd GestionnairePontons

# Sans git sur le NAS (courant sur QNAP) — clone via conteneur Docker
mkdir GestionnairePontons && cd GestionnairePontons
docker run --rm -v "$(pwd):/repo" -w /repo alpine/git clone https://github.com/Samito-05/GestionnairePontons.git .
```

> `deploy.sh` (mise a jour) requiert que ce dossier soit un clone git (`.git/` present) — les deux methodes ci-dessus conviennent.

### 2. Creer le fichier de configuration production

```bash
cp .env.production.example .env.production
```

Editer `.env.production` :

```env
DJANGO_SECRET_KEY=<cle generee — voir commande ci-dessous>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=pontons.mondomaine.com
TUNNEL_TOKEN=<token Cloudflare — obtenu a l'etape 4>
```

Generer une cle secrete :

```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

> Si la cle contient des caracteres `$`, les echapper en `$$` dans le fichier `.env.production`.
> Docker Compose interprete `$VAR` comme une substitution de variable shell.

### 3. Demarrer l'application

```bash
docker compose up -d --build

# Initialiser la base de donnees (premier demarrage uniquement)
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

Verification :

```bash
docker compose ps              # web: Up, tunnel: Up (ou Down si tunnel pas encore configure)
curl -I http://127.0.0.1:8000  # Attendu : HTTP/1.1 302 Found
```

### 4. Configurer le tunnel Cloudflare

1. Aller sur [one.dash.cloudflare.com](https://one.dash.cloudflare.com) → **Networks → Tunnels**
2. **Create a tunnel** → **Cloudflared** → donner un nom → **Save tunnel**
3. Copier le token affiche, le coller dans `.env.production` (`TUNNEL_TOKEN=...`)
4. Dans l'onglet **Public Hostnames**, ajouter :

| Champ | Valeur |
|---|---|
| Subdomain | `pontons` (ou autre) |
| Domain | `mondomaine.com` |
| Service Type | `HTTP` |
| URL | `web:8000` |

5. Relancer le service tunnel pour prendre en compte le token :

```bash
docker compose up -d --build tunnel
```

### Mise a jour

```bash
./deploy.sh
```

`git pull` (via conteneur Docker `alpine/git`, le NAS n'a pas git installe), rebuild, redemarre le container et joue les migrations. Ne touche pas `.env.production` (gitignore).

> **Migration conteneur non-root (une seule fois)** — le conteneur tourne desormais avec l'utilisateur `app` (non-root). Si les volumes datent d'une version precedente (fichiers appartenant a root), corriger les permissions une fois :
> ```bash
> docker compose run --rm --user root web chown -R app:app /app/data /app/media
> docker compose restart web
> ```

### Commandes utiles

```bash
docker compose logs -f                              # Logs en temps reel
docker compose logs tunnel                          # Logs du tunnel Cloudflare
docker compose restart web                          # Redemarrer sans rebuild
docker compose down                                 # Arreter tout

# Sauvegarde de la base de donnees
sh backup.sh
```

### Depannage

| Symptome | Cause probable | Solution |
|---|---|---|
| 502 Bad Gateway | Conteneur `web` arrete | `docker compose up -d` |
| Tunnel inactif dans Cloudflare | Token absent ou incorrect | Verifier `TUNNEL_TOKEN` dans `.env.production` |
| Erreur 500 | Erreur applicative | `docker compose logs web` |
| `DisallowedHost` dans les logs | Domaine absent de `ALLOWED_HOSTS` | Ajouter le domaine dans `.env.production` puis `docker compose restart web` |
| Medias perdus apres rebuild | Volume non monte | Verifier `media_data` dans `docker-compose.yml` |

---

## Fonctionnalites

### Planning
- Grille horaire par embarcation et par ponton
- Fenetre temporelle dynamique calculee depuis les locations du jour (fallback 13h-20h)
- Blocs colores selon la couleur de l'embarcation
- Indicateur de l'heure courante
- Navigation jour precedent / suivant / aujourd'hui
- Rafraichissement automatique toutes les 60 secondes

### Gestion rapide (gestionnaire)
- Vue kanban par ponton : 3 etats — disponible (vert) / reservee (jaune) / sortie (rouge)
- Workflow 2 etapes : **Reserver** (caisse, nom du client) → **Sortir** (ponton, chrono demarre au depart reel)
- Retour anticipe en 1 clic
- Nom du client affiche en evidence sur la carte (reservee et sortie)
- Heure de retour prevue affichee en temps reel
- Rafraichissement automatique toutes les 30 secondes

### Administration
- Tableau de bord avec compteurs
- CRUD : pontons, embarcations, locations, utilisateurs
- Validation des chevauchements de reservation
- Gestion des roles utilisateurs

### PWA
- Installable sur l'ecran d'accueil Android, iOS, desktop
- Fichiers statiques mis en cache (cache-first)
- HTML toujours charge depuis le serveur (jamais mis en cache)

---

## Roles et permissions

| Role | Acces |
|---|---|
| Visiteur (non connecte ou role visiteur) | Planning en lecture seule, navigation par date |
| Gestionnaire | + Louer une embarcation, enregistrer un retour |
| Admin | + CRUD complet pontons / embarcations / locations / utilisateurs |
| Superuser Django | Acces a l'interface `/admin/` native |

---

## Modele de donnees

```
Ponton
  nom, description, ordre, actif

  Embarcation
    nom, type, couleur (hex), ordre, actif
    --> ForeignKey Ponton

    Location
      heure_debut, heure_fin, statut (reservee|sortie), returned_at,
      is_manual, notes, created_at
      --> ForeignKey Embarcation
      --> ForeignKey User (gestionnaire)

User (Django natif)
  UserProfile
    role : admin | gestionnaire | visiteur
    --> OneToOne User
```

---

## URLs

| URL | Acces |
|---|---|
| `/` | Redirige vers planning |
| `/planning/` | Public |
| `/planning/?date=YYYY-MM-DD` | Public |
| `/planning/row/<id>/` | Public (partial HTMX, polling) |
| `/gestionnaire/` | Gestionnaire+ |
| `/gestionnaire/louer/<id>/` | Gestionnaire+ |
| `/gestionnaire/sortir/<id>/` | Gestionnaire+ |
| `/gestionnaire/retour/<id>/` | Gestionnaire+ |
| `/gestion/` | Admin |
| `/gestion/pontons/` | Admin |
| `/gestion/embarcations/` | Admin |
| `/gestion/locations/` | Admin |
| `/gestion/users/` | Admin |
| `/api/status/` | Public (JSON temps reel) |
| `/admin/` | Superuser Django |

---

## Structure du projet

```
GestionnairePontons/
├── config/
│   ├── settings.py          # Configuration Django (secrets via variables d'environnement)
│   ├── urls.py              # Routes racine
│   └── wsgi.py
├── pontons/
│   ├── models.py            # Ponton, Embarcation, Location, UserProfile
│   ├── views.py             # Toutes les vues
│   ├── services.py          # Construction des donnees du planning
│   ├── forms.py             # Formulaires avec validation
│   ├── urls.py              # Routes de l'application
│   ├── admin.py             # Interface admin Django natif
│   └── management/
│       └── commands/
│           └── init_demo.py # Donnees de demonstration
├── templates/
│   ├── base.html
│   ├── registration/
│   │   └── login.html
│   └── pontons/
│       ├── planning.html
│       ├── gestionnaire.html
│       └── admin/           # Dashboard, pontons, embarcations, locations, users + formulaires
├── static/
│   ├── manifest.json        # Manifest PWA
│   ├── sw.js                # Service Worker v3
│   └── icons/               # Icones PWA et marque ville
├── Dockerfile
├── docker-compose.yml
├── .env.example             # Template configuration developpement (versionne, sans secrets)
├── .env.production.example  # Template configuration production (versionne, sans secrets)
├── .env                     # Configuration developpement reelle (gitignore)
├── .env.production          # Configuration production reelle (gitignore, sur le serveur)
├── startup.ps1              # Script de demarrage Windows (developpement)
├── startup.bat
├── deploy.sh                # Script de mise a jour production (NAS via SSH)
├── backup.sh                # Sauvegarde JSON horodatee (cron NAS)
├── requirements.txt
└── manage.py
```

---

## Maintenance — Aide-memoire

### Acces SSH au NAS

```bash
ssh admin@192.168.X.XXX        # IP locale du NAS (voir interface QNAP)
cd /share/homes/admin/GestionnairePontons
```

### Etat de l'application

```bash
docker compose ps                   # Statut des conteneurs (web, tunnel)
docker compose logs -f              # Logs en temps reel (Ctrl+C pour quitter)
docker compose logs web --tail=50   # 50 dernieres lignes du serveur Django
docker compose logs tunnel --tail=20 # Statut du tunnel Cloudflare
```

### Redemarrer

```bash
docker compose restart web          # Redemarrer le serveur (sans rebuild)
docker compose restart tunnel       # Redemarrer le tunnel
docker compose restart              # Tout redemarrer
```

### Mettre a jour l'application

```bash
./deploy.sh
```

Le script `deploy.sh` fait `git pull` (via conteneur Docker `alpine/git`, pas besoin de git sur le NAS), rebuild, redemarre le container et joue les migrations automatiquement. Il ne touche pas `.env.production`. Il est versionne dans le depot — present des le clone initial.

### Sauvegardes

```bash
# Sauvegarde manuelle (JSON horodate dans ./backups/, 30 conserves)
sh backup.sh

# Sauvegarde automatique quotidienne a 3h — ajouter au crontab du NAS :
crontab -e
# 0 3 * * * cd /share/homes/admin/GestionnairePontons && sh backup.sh >> backups/backup.log 2>&1

# Restaurer une sauvegarde
docker compose exec -T web python manage.py loaddata backups/backup_YYYYMMDD_HHMM.json
```

### Acceder a la base de donnees

```bash
# Shell Django interactif
docker compose exec web python manage.py shell
```

### Creer ou modifier un compte

```bash
# Nouveau superuser
docker compose exec web python manage.py createsuperuser

# Changer le mot de passe d'un utilisateur existant
docker compose exec web python manage.py changepassword <nom_utilisateur>
```

### Modifier la configuration production

```bash
vi /share/homes/admin/GestionnairePontons/.env.production
# Apres modification :
docker compose restart web
```

### Arreter et relancer depuis zero

```bash
docker compose down              # Arrete les conteneurs (volumes conserves)
docker compose up -d --build     # Repart avec rebuild de l'image
```

> Pour supprimer aussi les donnees (volumes) : `docker compose down -v`
> Irreversible — toute la base de donnees est perdue.

### Verifier la connectivite du tunnel

```bash
# Depuis le NAS : l'app repond localement
curl -I http://127.0.0.1:8000

# Depuis le navigateur : l'app repond via Cloudflare
# https://pontons.MONDOMAINE.COM
```

---

## Licence

Projet libre d'utilisation.
