# 🕌 Mosquée Manager

> Gestion complète d'une mosquée : école coranique, adhésions, trésorerie, cagnottes, tableau de bord KPI public.

**Stack technique**

| Couche | Technologie |
|--------|-------------|
| Backend | Django 5.1.5 · Django REST Framework 3.15 · JWT (simplejwt) |
| Base de données | PostgreSQL 16 |
| Frontend | HTML/CSS/JS pur — aucun framework, aucun build step |
| Infrastructure | Docker Compose · Gunicorn · Nginx · Raspberry Pi |
| Tests | pytest 8.3.5 · pytest-django · 113 tests automatisés |

**Multi-tenant** — chaque donnée est isolée par mosquée (`mosque_id` sur tous les modèles). Une instance = plusieurs mosquées possibles sur le même serveur.

---

## 📋 Table des matières

1. [Fonctionnalités](#fonctionnalités)
2. [Architecture](#architecture)
3. [Installation — développement local](#installation--développement-local)
4. [Variables d'environnement](#variables-denvironnement)
5. [Démarrer le projet](#démarrer-le-projet)
6. [Onboarding — première configuration](#onboarding--première-configuration)
7. [API — Endpoints](#api--endpoints)
8. [Frontend](#frontend)
9. [Tests automatisés](#tests-automatisés)
10. [Déploiement en production (Raspberry Pi)](#déploiement-en-production-raspberry-pi)
11. [Multi-instances](#multi-instances)
12. [Backup & Restauration](#backup--restauration)
13. [Structure du projet](#structure-du-projet)
14. [Roadmap](#roadmap)

---

## Fonctionnalités

### 🏫 École coranique
- Gestion des familles et enfants (niveaux, groupes)
- Paiements des frais de scolarité (annuel / par personne)
- Liste des familles en retard de paiement (arrears)
- Génération de reçus PDF individuels + envoi par email

### 👥 Adhésions
- Registre des membres de la mosquée
- Cotisations annuelles avec suivi des impayés
- Génération de reçus PDF + envoi par email

### 💰 Trésorerie
- Journal de toutes les entrées/sorties
- Catégories : dons, loyer, salaire, factures, projets…
- Régime fiscal (loi 1901 / loi 1905)
- Cagnottes avec objectif, progression, affichage public KPI

### 📊 Tableau de bord KPI (public)
- Endpoint public, aucune authentification requise
- Aucune donnée personnelle (PII) — uniquement compteurs et totaux
- Paramétrable par widget (école / adhésions / trésorerie / cagnottes)
- Rafraîchissement automatique configurable (idéal écran TV)
- Filtrable par mois pour la trésorerie

### 🔐 RBAC (Contrôle d'accès par rôle)

| Rôle | Accès |
|------|-------|
| `ADMIN` | Tout : utilisateurs, paramètres, audit, toutes les apps |
| `ECOLE_MANAGER` | École uniquement |
| `TRESORIER` | Trésorerie + adhésions |

### 📋 Audit Log
- Toutes les actions CREATE / UPDATE / DELETE tracées
- Accessible uniquement aux ADMINs
- Filtrable par action (`?action=CREATE`) et entité (`?entity=Family`)

### 📧 Notifications email
- Reçus PDF envoyés par email
- Configuration SMTP par mosquée dans les paramètres Admin
- Endpoint de test `/api/notifications/test/`

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Raspberry Pi                     │
│                                                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────────┐  │
│  │  Nginx   │───▶│ Gunicorn │───▶│   Django     │  │
│  │ (static) │    │ (WSGI)   │    │   + DRF      │  │
│  └──────────┘    └──────────┘    └──────┬───────┘  │
│                                         │           │
│                                  ┌──────▼───────┐  │
│                                  │  PostgreSQL  │  │
│                                  │     16       │  │
│                                  └──────────────┘  │
└─────────────────────────────────────────────────────┘
```

```
Django apps :
  core/        → User, Mosque, MosqueSettings, AuditLog, permissions
  school/      → Family, Child, SchoolYear, SchoolPayment
  membership/  → Member, MembershipYear, MembershipPayment
  treasury/    → TreasuryTransaction, Campaign
  kpi/         → Vues publiques agrégées (aucun PII)
```

---

## Installation — développement local

### Prérequis

| Outil | Version |
|-------|---------|
| Docker | 24+ |
| Docker Compose | v2 (plugin intégré) |
| Git | n'importe |

> Pas besoin de Python, PostgreSQL ou Node.js en local — tout tourne dans Docker.

```bash
# 1. Cloner
git clone https://github.com/BadreddineEK/MManager.git
cd MManager

# 2. Configurer l'environnement
cp .env.example .env
# Éditer .env (voir section Variables d'environnement)

# 3. Démarrer la stack de développement
docker compose up -d

# 4. Appliquer les migrations
docker compose exec backend python manage.py migrate

# 5. Créer le super-utilisateur Django
docker compose exec backend python manage.py createsuperuser

# 6. Créer la première mosquée via l'Admin Django
# → http://localhost:8000/admin/
```

---

## Variables d'environnement

Copier `.env.example` → `.env` et remplir :

```env
# ── Base de données ───────────────────────────────────────
POSTGRES_DB=mmanager
POSTGRES_USER=mmanager
POSTGRES_PASSWORD=changeme_db

# ── Django ────────────────────────────────────────────────
SECRET_KEY=changeme_secret_key_very_long_random_string
DEBUG=True                    # False en production
ALLOWED_HOSTS=localhost,127.0.0.1

# ── CORS ──────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# ── Email (optionnel — configurable aussi par mosquée) ────
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
```

---

## Démarrer le projet

### Développement

```bash
docker compose up -d

# Logs backend
docker compose logs -f backend

# Arrêter
docker compose down
```

| Service | URL |
|---------|-----|
| API | `http://localhost:8000/api/` |
| Admin Django | `http://localhost:8000/admin/` |
| Frontend | Ouvrir `frontend/index.html` dans le navigateur |

### Production (profil prod)

```bash
docker compose --profile prod up -d
```

---

## Onboarding — première configuration

> ✨ **Auto-init** : à la création d'une mosquée, `MosqueSettings`, `SchoolYear` et `MembershipYear` sont créés automatiquement par signal Django.

```
1. Admin Django (/admin/)
2. Créer une Mosque   → nom + slug unique + timezone
                        ↳ MosqueSettings + SchoolYear + MembershipYear créés auto
3. Configurer les paramètres → frais scolarité, cotisation, SMTP, widgets KPI
4. Créer les utilisateurs    → rôle ADMIN / ECOLE_MANAGER / TRESORIER
5. ✅ Prêt
```

> ⚠️ **Multi-mosquée** : chaque utilisateur est rattaché à **une seule mosquée** (`mosque_id`).  
> Le compte superuser Django (admin) n'est rattaché à aucune mosquée — il sert uniquement à l'administration Django.  
> Pour accéder à l'application, utiliser un compte utilisateur normal avec rôle `ADMIN`.

---

## API — Endpoints

Toutes les routes sont préfixées par `/api/`.
Authentification requise (sauf KPI) : `Authorization: Bearer <access_token>`

### Auth

| Méthode | URL | Description |
|---------|-----|-------------|
| `POST` | `/api/auth/login/` | Login → access + refresh tokens |
| `POST` | `/api/auth/refresh/` | Renouveler l'access token |
| `POST` | `/api/auth/logout/` | Invalider le refresh token |

### École

| Méthode | URL | Description |
|---------|-----|-------------|
| `GET/POST` | `/api/school/families/` | Liste / créer famille |
| `GET/PATCH/DELETE` | `/api/school/families/{id}/` | Détail famille |
| `GET` | `/api/school/families/arrears/` | Familles en retard |
| `GET/POST` | `/api/school/children/` | Enfants |
| `GET/POST` | `/api/school/payments/` | Paiements école |
| `GET` | `/api/school/payments/{id}/receipt/` | Reçu PDF |
| `POST` | `/api/school/payments/{id}/send-receipt/` | Envoyer reçu email |

### Adhésions

| Méthode | URL | Description |
|---------|-----|-------------|
| `GET/POST` | `/api/membership/members/` | Membres |
| `GET` | `/api/membership/members/unpaid/` | Membres sans cotisation (année active) |
| `GET/POST` | `/api/membership/years/` | Années de cotisation |
| `GET/POST` | `/api/membership/payments/` | Paiements cotisation |
| `GET` | `/api/membership/receipt/payment/{id}/` | Reçu PDF cotisation adhérent |

### Trésorerie

| Méthode | URL | Description |
|---------|-----|-------------|
| `GET/POST` | `/api/treasury/transactions/` | Journal de trésorerie |
| `GET` | `/api/treasury/transactions/summary/` | Solde (cumulé ou par mois) |
| `GET/POST` | `/api/treasury/campaigns/` | Cagnottes |
| `PATCH` | `/api/treasury/campaigns/{id}/` | Mettre à jour cagnotte |
| `GET` | `/api/treasury/receipt/transaction/{id}/` | Reçu PDF transaction |
| `GET` | `/api/treasury/receipt/annual/` | Récap annuel dons PDF |

### KPI — Public (sans authentification)

| Méthode | URL | Description |
|---------|-----|-------------|
| `GET` | `/api/kpi/mosques/` | Liste des mosquées |
| `GET` | `/api/kpi/summary/?mosque=<slug>` | Agrégats KPI complets |
| `GET` | `/api/kpi/summary/?mosque=<slug>&month=2026-03` | Filtré par mois |

### Admin

| Méthode | URL | Description |
|---------|-----|-------------|
| `GET/POST` | `/api/users/` | Utilisateurs (ADMIN) |
| `GET` | `/api/users/me/` | Profil connecté |
| `GET` | `/api/audit/` | Journal d'audit (ADMIN) |
| `GET/PATCH` | `/api/settings/` | Paramètres mosquée |
| `POST` | `/api/notifications/test/` | Tester l'envoi email |

---

## Frontend

Application web statique — aucun framework, aucun build, aucune dépendance npm.

```
frontend/
├── index.html          → Application principale (authentifiée)
├── kpi.html            → Tableau de bord public (TV / tablette)
├── css/
│   └── styles.css
└── js/
    ├── api.js          → Client HTTP (fetch + gestion JWT)
    ├── auth.js         → Login / logout / gestion tokens
    ├── nav.js          → Navigation et routing SPA
    ├── dashboard.js    → Vue d'accueil
    ├── school.js       → Module école
    ├── membership.js   → Module adhésions
    ├── treasury.js     → Module trésorerie
    ├── campaigns.js    → Module cagnottes
    ├── audit.js        → Journal d'audit
    ├── users.js        → Gestion utilisateurs
    ├── settings.js     → Paramètres mosquée
    ├── notifications.js→ Test email
    ├── export.js       → Export CSV/PDF
    └── ui.js           → Composants UI partagés
```

En production, les fichiers sont servis directement par Nginx.  
En développement, ouvrir `frontend/index.html` directement dans le navigateur.

---

## Tests automatisés

```bash
# Tous les tests
docker compose exec backend pytest -q

# Mode verbeux
docker compose exec backend pytest -v

# Une app seulement
docker compose exec backend pytest school/tests.py -v

# Script pré-déploiement
./scripts/run_tests.sh
```

### Résultat actuel : **113 tests ✅**

| App | Tests | Couverture |
|-----|-------|------------|
| `core` | 27 | Auth JWT, RBAC, Audit Log, gestion utilisateurs |
| `kpi` | 20 | Endpoint public, agrégats, isolation multi-tenant, absence de PII |
| `school` | 15 | CRUD familles/enfants, paiements, arrears, isolation |
| `membership` | 15 | CRUD membres, paiements, unpaid, isolation |
| `treasury` | 12 | CRUD transactions, cagnottes, isolation |

---

## Déploiement en production (Raspberry Pi)

### Première installation

Voir `INSTALL.md` pour le guide complet.

```bash
git clone https://github.com/BadreddineEK/MManager.git
cd MManager
cp .env.example .env
# Éditer .env : DEBUG=False, SECRET_KEY forte, ALLOWED_HOSTS

docker compose --profile prod up -d
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
```

### Mise à jour

```bash
cd /home/mosquee/MManager
git pull origin main
docker compose --profile prod build --no-cache backend
docker compose --profile prod up -d
docker compose exec backend python manage.py migrate

# Vérification
docker compose exec backend pytest -q
# → 89 passed ✅
```

> ⚠️ **Règle absolue** : ne jamais modifier les fichiers directement sur le Pi.  
> Tout changement passe par `git push` depuis le Mac → `git pull` sur le Pi.

---

## Multi-instances

Une mosquée = un Raspberry Pi = une instance indépendante.

```bash
# Mettre à jour toutes les mosquées d'un coup
./scripts/update_all.sh

# Instances configurées
cat scripts/instances.conf
```

Voir `DEPLOY-NEW-MOSQUE.md` pour déployer une nouvelle instance.

---

## Backup & Restauration

```bash
# Backup manuel
docker compose exec backend python manage.py dumpdata \
  --natural-foreign --indent 2 > backups/backup_$(date +%Y%m%d).json

# Restaurer
docker compose exec backend python manage.py loaddata backups/backup_YYYYMMDD.json
```

Un service de backup automatique est inclus dans `docker-compose.yml`.

---

## Structure du projet

```
MManager/
├── backend/
│   ├── config/             → settings.py, urls.py, wsgi.py, asgi.py
│   ├── core/               → User, Mosque, AuditLog, permissions, utils
│   ├── school/             → Family, Child, SchoolYear, SchoolPayment
│   ├── membership/         → Member, MembershipYear, MembershipPayment
│   ├── treasury/           → TreasuryTransaction, Campaign
│   ├── kpi/                → Vues publiques agrégées (KPI)
│   ├── templates/          → Templates HTML (reçus PDF)
│   ├── conftest.py         → Fixtures pytest partagées
│   ├── pytest.ini          → Configuration pytest
│   ├── manage.py
│   ├── Dockerfile
│   ├── entrypoint.sh
│   └── requirements.txt
├── frontend/
│   ├── index.html          → App principale
│   ├── kpi.html            → Dashboard public
│   ├── css/styles.css
│   └── js/                 → 14 modules JS
├── nginx/nginx.conf
├── scripts/
│   ├── run_tests.sh        → Tests pré-déploiement
│   ├── update_all.sh       → Mise à jour multi-instances
│   ├── backup.sh           → Backup automatique
│   └── instances.conf      → Liste des Pi
├── backups/
├── docker-compose.yml
├── .env.example
├── INSTALL.md              → Guide d'installation Pi
├── DEPLOY-NEW-MOSQUE.md    → Ajouter une nouvelle instance
└── WORKFLOW-DEV.md         → Règles de développement
```

---

## Roadmap

- [x] **Step 1** — École coranique (familles, enfants, paiements, reçus PDF)
- [x] **Step 2** — Adhésions (membres, cotisations, reçus PDF)
- [x] **Step 3** — Trésorerie (transactions, catégories, régime fiscal)
- [x] **Step 4** — Cagnottes avec progression et affichage KPI
- [x] **Step 5** — RBAC granulaire (ADMIN / ECOLE_MANAGER / TRESORIER)
- [x] **Step 6** — Frontend modulaire (14 modules JS, SPA)
- [x] **Step 7** — Audit Log + Notifications email
- [x] **Step 8** — Tests automatisés (113 tests pytest — core, school, membership, treasury, kpi)
- [ ] **Step 9** — Import / Migration de données (CSV / Excel)
- [ ] **Step 10** — Saisie rapide multi-transactions (tableau inline)
- [ ] **Step 11** — Intégration HelloAsso / Cotizup (webhook)
- [ ] **Step 12** — IA scan relevé bancaire (OCR + suggestion catégorie)
- [ ] **Step 13** — Rapport comptable annuel PDF (compte de résultat)

---

*Conçu pour les associations et mosquées — hébergeable sur un Raspberry Pi à ~35€.*
