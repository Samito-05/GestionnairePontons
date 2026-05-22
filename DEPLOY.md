# Guide de déploiement — GestionnairePontons

**Stack :** QNAP NAS + Docker + Cloudflare Tunnel  
**Résultat :** `https://pontons.tondomaine.com` accessible depuis n'importe où, sans ouvrir de ports sur ta box

---

## Vue d'ensemble

```
Navigateur  →  Cloudflare (HTTPS)  →  Tunnel chiffré  →  QNAP (Docker, port 8000)
```

Cloudflare gère le HTTPS. Le NAS n'est jamais directement exposé à Internet.

---

## Prérequis

- QNAP avec **Container Station** installé (App Center → chercher "Container Station")
- Un compte **Cloudflare** gratuit avec un domaine ajouté ([cloudflare.com](https://cloudflare.com))
- Accès SSH au NAS activé (Panneau de configuration → Réseau et services de fichiers → Telnet/SSH → Activer SSH)
- Git installé sur le NAS (App Center → chercher "Git" ou via SSH : `opkg install git`)

---

## Étape 1 — Vérifier l'architecture du NAS

Connecte-toi en SSH au NAS. Sur Windows, ouvre PowerShell :

```bash
ssh admin@192.168.1.XXX
# Remplace XXX par l'IP locale du NAS (visible dans l'interface QNAP)
# Accepte l'empreinte SSH (yes), entre ton mot de passe admin
```

Une fois connecté, vérifie l'architecture :

```bash
uname -m
```

Note le résultat — ça sera soit `x86_64` (processeur Intel/AMD) soit `aarch64` (processeur ARM).  
Tu en auras besoin à l'**Étape 5** pour télécharger le bon `cloudflared`.

---

## Étape 2 — Cloner le code sur le NAS

Toujours dans SSH, choisis un emplacement pour le code :

```bash
cd /share/homes/admin
# ou un partage dédié, ex: /share/MonProjet

git clone https://github.com/Samito-05/GestionnairePontons.git
cd GestionnairePontons
```

---

## Étape 3 — Créer le fichier de configuration production

Ce fichier contient tes secrets — il ne sera **jamais** commité dans Git.

```bash
cp .env.production.example .env.production
```

Ouvre-le pour l'éditer :

```bash
nano .env.production
```

Tu verras :

```
DJANGO_SECRET_KEY=generate-a-fresh-key-here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=pontons.example.com
```

**Génère une vraie clé secrète :**

```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Si Python n'est pas dispo sur le NAS, génère-la sur ton PC Windows (dans le dossier du projet) :

```powershell
python manage.py shell -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copie la clé générée. Édite `.env.production` :

```
DJANGO_SECRET_KEY=COLLE_TA_CLE_ICI
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=pontons.tondomaine.com
```

> **Remplace `pontons.tondomaine.com`** par le vrai sous-domaine que tu vas utiliser.  
> Ex : si ton domaine est `dupont.fr`, mets `pontons.dupont.fr`

Sauvegarde : `Ctrl+O` → Entrée → `Ctrl+X`

---

## Étape 4 — Lancer l'application avec Docker

### 4a — Construire et démarrer

```bash
docker compose up -d --build
```

- `--build` : construit l'image (prend 2-3 min la première fois)
- `-d` : démarre en arrière-plan

Vérifie que le conteneur tourne :

```bash
docker compose ps
```

Tu dois voir `web` avec le statut `Up`.

### 4b — Initialiser la base de données

```bash
docker compose exec web python manage.py migrate
```

### 4c — Créer le compte administrateur

```bash
docker compose exec web python manage.py createsuperuser
```

Suis les instructions (nom d'utilisateur, email, mot de passe).

### 4d — Test local

Depuis le NAS lui-même, vérifie que l'appli répond :

```bash
curl -I http://127.0.0.1:8000
# Doit retourner: HTTP/1.1 301 ou 200
```

---

## Étape 5 — Installer Cloudflare Tunnel (`cloudflared`)

### 5a — Créer un tunnel dans Cloudflare

1. Va sur [one.dash.cloudflare.com](https://one.dash.cloudflare.com)
2. Menu gauche : **Networks → Tunnels**
3. Clique **Create a tunnel**
4. Choisis **Cloudflared** → **Next**
5. Nomme-le `gestionnaire-pontons` → **Save tunnel**
6. Sur la page suivante, Cloudflare te montre une commande d'installation. **Ne ferme pas cette page.**

### 5b — Télécharger `cloudflared` sur le NAS

Dans le terminal SSH du NAS, télécharge le bon binaire selon ton architecture (vue à l'**Étape 1**) :

**Si `x86_64` (Intel/AMD) :**
```bash
cd /usr/local/bin
sudo wget -O cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
sudo chmod +x cloudflared
```

**Si `aarch64` (ARM) :**
```bash
cd /usr/local/bin
sudo wget -O cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64
sudo chmod +x cloudflared
```

Vérifie :
```bash
cloudflared --version
# Doit afficher: cloudflared version X.X.X
```

### 5c — Authentifier `cloudflared`

Dans la page Cloudflare (étape 5a), copie le token affiché. Il ressemble à :

```
eyJhIjoiMW...très long token...
```

Sur le NAS, lance :

```bash
cloudflared service install eyJhIjoiMW...TON_TOKEN_ICI...
```

> Colle le token **en entier** — il est très long, c'est normal.

`cloudflared` va démarrer comme service et se connecter à Cloudflare.

### 5d — Configurer le hostname public

Retourne dans le dashboard Cloudflare :

1. Clique **Next** (après l'installation)
2. Section **Public Hostnames** → **Add a public hostname**
3. Remplis :
   - **Subdomain :** `pontons` (ou ce que tu veux)
   - **Domain :** `tondomaine.com`
   - **Service Type :** `HTTP`
   - **URL :** `127.0.0.1:8000`
4. Clique **Save tunnel**

---

## Étape 6 — Vérifier le déploiement

Ouvre ton navigateur et va sur `https://pontons.tondomaine.com`

Tu dois voir la page de connexion de l'application.

- Le cadenas HTTPS est présent ✅
- Connexion avec le compte créé à l'**Étape 4c** ✅

---

## Étape 7 — Démarrage automatique au redémarrage du NAS

Le conteneur Docker redémarre tout seul (`restart: unless-stopped` dans `docker-compose.yml`).

Pour `cloudflared`, s'il n'a pas été installé comme service système (étape 5c), crée une tâche planifiée dans QNAP :  
**Panneau de configuration → Planificateur de tâches → Créer → Tâche déclenchée** → événement : démarrage du système → commande :
```
cloudflared service install
```

---

## Mise à jour de l'application

Quand tu fais des modifications et que tu pousses sur GitHub :

```bash
# Sur le NAS, dans /share/homes/admin/GestionnairePontons
ssh admin@192.168.1.XXX
cd /share/homes/admin/GestionnairePontons

git pull
docker compose up -d --build
docker compose exec web python manage.py migrate   # si migrations
```

---

## Commandes utiles

```bash
# Voir les logs en temps réel
docker compose logs -f

# Arrêter l'application
docker compose down

# Redémarrer sans reconstruire
docker compose restart

# Accéder au shell Django
docker compose exec web python manage.py shell

# Sauvegarder la base de données
docker compose exec web python manage.py dumpdata > backup_$(date +%Y%m%d).json
```

---

## Dépannage

| Problème | Cause probable | Solution |
|---|---|---|
| Site inaccessible, erreur 502 | Conteneur Docker arrêté | `docker compose up -d` |
| Site inaccessible, erreur 1033 | Tunnel Cloudflare déconnecté | `cloudflared service start` sur le NAS |
| Page blanche ou erreur 500 | Erreur applicative | `docker compose logs -f` pour voir l'erreur |
| "DisallowedHost" dans les logs | Domaine absent de `ALLOWED_HOSTS` | Ajouter le domaine dans `.env.production` puis `docker compose restart` |
| Fichiers media (photos) perdus | Volume Docker non persisté | Vérifier que `docker-compose.yml` a bien le volume `media_data` |

---

## Sécurité — Rappels

- `.env.production` contient des secrets — **ne jamais le commiter** (il est dans `.gitignore`)
- `DJANGO_DEBUG=False` en production — ne jamais mettre `True` sur le serveur
- La clé secrète de dev (dans `.env`) est différente de la clé de prod — **ne pas réutiliser**
- Cloudflare Tunnel chiffre tout le trafic — pas besoin d'ouvrir des ports sur ta box internet
