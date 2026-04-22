# 🚤 Gestionnaire Pontons

Application web de gestion de locations d'embarcations (pédalos, kayaks, canoës, SUP…) avec planning visuel, interface gestionnaire et administration complète.

> Installable comme application mobile (PWA) — fonctionne sur Android, iOS et desktop.

---

## Aperçu

| Vue | Accès | Description |
|-----|-------|-------------|
| **Planning** | Public | Grille horaire 13h–20h, toutes embarcations |
| **Gestion rapide** | Gestionnaire | Louer / retourner en 1 clic |
| **Administration** | Admin | CRUD complet, utilisateurs, historique |

---

## Stack technique

- **Backend** : Django 5.2 (Python 3.12)
- **Base de données** : SQLite (remplaçable par MySQL/PostgreSQL)
- **CSS** : [Bulma 1.0](https://bulma.io/) + Font Awesome 6
- **Fichiers statiques** : WhiteNoise
- **Mobile** : PWA (manifest + service worker, mode offline)

---

## Installation

### Prérequis

- Python 3.10+
- pip

### Étapes

```bash
# 1. Cloner le dépôt
git clone https://github.com/Samito-05/GestionnairePontons.git
cd GestionnairePontons

# 2. Créer un environnement virtuel (recommandé)
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Appliquer les migrations
python manage.py migrate

# 5. Charger les données de démonstration
python manage.py init_demo

# 6. Lancer le serveur
python manage.py runserver
```

Ouvrir : [http://127.0.0.1:8000](http://127.0.0.1:8000)

### Demarrage en une commande (Windows)

Un script complet est fourni a la racine du projet :

```powershell
# Lance toute la sequence: venv -> dependances -> migrations -> demo -> serveur
.\startup.ps1

# Equivalent via batch (double-clic possible)
.\startup.bat
```

Options utiles :

```powershell
# Prepare l'environnement sans demarrer le serveur
.\startup.ps1 -NoRunServer

# Ignore l'installation des dependances
.\startup.ps1 -SkipInstall

# Ignore l'initialisation des donnees de demo
.\startup.ps1 -SkipDemo

# Reinitialise la base SQLite puis relance les migrations
.\startup.ps1 -ResetDatabase

# Change le port
.\startup.ps1 -Port 8080
```

---

## Comptes par défaut

| Identifiant | Mot de passe | Rôle |
|-------------|-------------|------|
| `admin` | `admin123` | Superadmin (accès total) |
| `gestionnaire1` | `gest123` | Gestionnaire |
| `visiteur1` | `visit123` | Visiteur (lecture seule) |

> ⚠️ Changer les mots de passe avant tout déploiement en production.

---

## Rôles et permissions

### Visiteur (non connecté ou rôle visiteur)
- Consulter le planning du jour (lecture seule)
- Naviguer entre les dates

### Gestionnaire
- Tout ce que le visiteur peut faire
- **Louer** une embarcation disponible (durée fixe : 1 heure)
- **Marquer le retour** anticipé d'une embarcation
- Voir le statut en temps réel (disponible / sortie)

### Admin
- Tout ce que le gestionnaire peut faire
- **Pontons** : créer, renommer, réordonner, activer/désactiver
- **Embarcations** : créer, modifier couleur/type/ponton, désactiver
- **Locations** : créer, modifier, supprimer manuellement
- **Utilisateurs** : créer des comptes, assigner les rôles, supprimer

---

## Fonctionnalités

### Planning (13h–20h)
- Grille par tranche de **30 minutes** (14 colonnes) × embarcations
- Regroupement par ponton
- Blocs colorés selon la couleur de l'embarcation
- Indicateur de l'heure courante
- Navigation jour précédent / suivant / aujourd'hui
- **Rafraîchissement automatique** toutes les 60 secondes
- Résumé en bas : statut disponible / sortie par embarcation

### Gestion rapide
- Vue kanban par ponton
- Carte verte = disponible → bouton **Louer 1h** avec champ notes
- Carte rouge = sortie → heure de retour prévue + bouton **Retour anticipé**
- **Rafraîchissement automatique** toutes les 30 secondes

### Administration
- Tableau de bord avec compteurs (pontons, embarcations, locations du jour, utilisateurs)
- Sidebar de navigation sur desktop
- Formulaires avec validation (chevauchement de réservation détecté)
- Gestion des locations manuelles (créneau libre choisi)

### PWA (Progressive Web App)
- Installable sur l'écran d'accueil Android/iOS/desktop
- Mode offline : le planning en cache reste consultable
- Icônes et raccourcis (Planning, Gestion rapide)

---

## Structure du projet

```
GestionnairePontons/
├── config/                     # Configuration Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── pontons/                    # Application principale
│   ├── models.py               # Ponton, Embarcation, Location, UserProfile
│   ├── views.py                # Toutes les vues
│   ├── forms.py                # Formulaires avec validation
│   ├── urls.py                 # Routes
│   ├── admin.py                # Interface admin Django
│   └── management/
│       └── commands/
│           └── init_demo.py    # Commande de démo
├── templates/
│   ├── base.html               # Template de base (Bulma, navbar)
│   ├── registration/
│   │   └── login.html          # Page de connexion
│   └── pontons/
│       ├── planning.html       # Grille planning 13h–20h
│       ├── gestionnaire.html   # Interface de gestion rapide
│       └── admin/              # Tous les templates admin
│           ├── base_admin.html
│           ├── dashboard.html
│           ├── pontons.html / ponton_form.html
│           ├── embarcations.html / embarcation_form.html
│           ├── locations.html / location_form.html
│           └── users.html / user_form.html
├── static/
│   ├── manifest.json           # Manifest PWA
│   ├── sw.js                   # Service worker (offline)
│   └── icons/                  # Icônes PWA 192×192 et 512×512
├── manage.py
├── requirements.txt
└── db.sqlite3                  # Base de données (ignorée en prod)
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

| URL | Vue | Accès |
|-----|-----|-------|
| `/` | Redirige vers planning | Public |
| `/login/` | Connexion | Public |
| `/planning/` | Planning du jour | Public |
| `/planning/?date=YYYY-MM-DD` | Planning d'une date | Public |
| `/gestionnaire/` | Gestion rapide | Gestionnaire+ |
| `/gestionnaire/louer/<id>/` | Louer une embarcation | Gestionnaire+ |
| `/gestionnaire/retour/<id>/` | Retour anticipé | Gestionnaire+ |
| `/gestion/` | Tableau de bord admin | Admin |
| `/gestion/pontons/` | Gestion des pontons | Admin |
| `/gestion/embarcations/` | Gestion des embarcations | Admin |
| `/gestion/locations/` | Historique des locations | Admin |
| `/gestion/users/` | Gestion des utilisateurs | Admin |
| `/api/status/` | Statut JSON temps réel | Public |
| `/admin/` | Admin Django natif | Superuser |

---

## Configuration

### Passer à MySQL

Dans `config/settings.py`, remplacer le bloc `DATABASES` :

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'pontons_db',
        'USER': 'mon_user',
        'PASSWORD': 'mon_mdp',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```

Puis : `pip install mysqlclient` et `python manage.py migrate`

### Variables d'environnement (production)

Avant de déployer, externaliser au minimum :

```python
# config/settings.py
import os
SECRET_KEY = os.environ['SECRET_KEY']
DEBUG = False
ALLOWED_HOSTS = ['mon-domaine.com']
```

---

## Déploiement rapide (production)

```bash
# Collecter les fichiers statiques
python manage.py collectstatic

# Créer un superuser si besoin
python manage.py createsuperuser

# Lancer avec Gunicorn (exemple)
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

---

## Développement

```bash
# Migrations après modification des modèles
python manage.py makemigrations && python manage.py migrate

# Réinitialiser les données de démo
python manage.py flush --no-input
python manage.py init_demo

# Vérification système Django
python manage.py check
```

---

## Licence

Projet libre d'utilisation. Adapter à vos besoins.
