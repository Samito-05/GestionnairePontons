# Gestionnaire Pontons

Application web de gestion de locations d'embarcations (pédalos, kayaks, canoës, barques, SUP) avec planning visuel, interface de gestion rapide et administration complète.

Installable comme application mobile (PWA) sur Android, iOS et desktop.

---

## Stack

| Composant | Version |
|---|---|
| Python | 3.14 (image Docker) |
| Django | 5.2 |
| Base de données | SQLite (dev et production, volume Docker sur le NAS) |
| CSS | Thème maritime custom (CSS variables, sans framework) |
| Icônes | Font Awesome 6 (CDN) |
| Fichiers statiques | WhiteNoise 6.12 avec CompressedManifestStaticFilesStorage |
| WSGI | Gunicorn 26 |
| Anti brute-force | django-axes 8 (5 echecs → compte verrouille 15 min) |
| Variables d'environnement | python-dotenv 1.2 |
| Déploiement | Docker + Cloudflare Tunnel, via [nas-stack](https://github.com/Samito-05/nas-stack) |
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

L'application tourne sur le NAS avec les autres projets, dans **[Samito-05/nas-stack](https://github.com/Samito-05/nas-stack)** : un seul tunnel Cloudflare, un seul `deploy.sh`, des sauvegardes communes. Tout y est décrit (installation, mise à jour, sauvegardes, restauration).

```
Navigateur  -->  Cloudflare (HTTPS)  -->  Tunnel chiffré  -->  conteneur pontons (port 8000, aucun port ouvert sur le NAS)
```

Ce dépôt fournit l'image : `Dockerfile` (migrations au démarrage, utilisateur non-root) et la sonde `/health` utilisée par le healthcheck.

Pour tester l'image de production en local :

```bash
cp .env.production.example .env.production   # remplir DJANGO_SECRET_KEY
docker compose up --build                     # http://127.0.0.1:8000
docker compose exec web python manage.py createsuperuser
```

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
| `/gestionnaire/retour/annuler/<id location>/` | Gestionnaire+ (annulation d'un retour, 60 s max) |
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
├── docker-compose.yml       # Test local de l'image (la prod est dans nas-stack)
├── .env.example             # Template configuration developpement (versionne, sans secrets)
├── .env.production.example  # Template configuration production (versionne, sans secrets)
├── .env                     # Configuration developpement reelle (gitignore)
├── .env.production          # Test local de l'image (gitignore) ; en production : env/pontons.env de nas-stack
├── startup.ps1              # Script de demarrage Windows (developpement)
├── startup.bat
├── .dockerignore            # Secrets, base et .git exclus de l'image
├── requirements.txt
└── manage.py
```

---

## Maintenance — Aide-memoire

Les commandes de production (mise à jour, sauvegardes, comptes, journaux) sont dans le README de **nas-stack**. Les plus courantes, depuis le dossier `nas-stack` sur le NAS (`ssh nas` depuis le PC, même hors de la maison : voir nas-stack, « Se connecter au NAS à distance ») :

```bash
sh deploy.sh pontons                                         # mettre à jour
docker compose exec pontons python manage.py createsuperuser # nouveau compte admin
docker compose exec pontons python manage.py changepassword NOM
docker compose logs --tail 50 pontons                        # journaux
```

## Licence

Projet libre d'utilisation.
