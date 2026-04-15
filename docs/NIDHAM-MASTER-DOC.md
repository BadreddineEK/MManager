# NIDHAM / MMANAGER — DOCUMENT MAÎTRE
## Migration Raspberry Pi → VPS Hetzner + Architecture Multi-Mosquée
### Version : avril 2026 | Repo : github.com/BadreddineEK/MManager

---

## 1. ÉTAT ACTUEL DU PROJET (au 07/04/2026)

### 1.1 Ce qui existe et fonctionne

Le repo [BadreddineEK/MManager](https://github.com/BadreddineEK/MManager) contient une application Django complète, tournant sur Raspberry Pi avec exposition via tunnel Cloudflare (ngrok-like).

**Structure du backend :**
```
backend/
├── config/          → settings Django, wsgi, urls racine
├── core/            → Mosquée, MosqueSettings, User, RBAC, Auth JWT
│   ├── models.py          (Mosque, MosqueSettings, CustomUser)
│   ├── middleware.py       (RBAC middleware en place)
│   ├── permissions.py      (permissions custom)
│   ├── import_views.py     (import Excel familles/enfants)
│   ├── export_views.py     (exports PDF fiscaux, Excel)
│   ├── notification_views.py (SMTP email)
│   ├── backup_views.py     (backup/restore BDD)
│   └── audit_views.py      (journal d'audit)
├── school/          → Classes, Élèves, Présences, Profs
├── membership/      → Familles, Adhésions, Cotisations
├── treasury/        → Dons, Paiements, Comptabilité
└── kpi/             → KPIs agrégés
```

**Stack actuelle :**
- Django 5.1.5 + DRF 3.15.2
- Auth JWT (simplejwt 5.3.1)
- PostgreSQL 16 (Docker)
- Gunicorn 21.2.0
- Nginx (config présente dans /nginx/)
- docker-compose.yml complet avec profil prod
- Backup cron quotidien (scripts/)
- Tests pytest présents (conftest.py, tests.py, tests_import.py)

**Ce qui est déjà là et prêt pour la prod :**
- ✅ docker-compose.yml avec profil `prod` (backend-prod + nginx)
- ✅ Gunicorn configuré (2 workers, 4 threads, timeout 120)
- ✅ Cloudflared tunnel déjà dans docker-compose (à remplacer par VPS)
- ✅ Backup cron à 2h du matin
- ✅ RBAC middleware présent
- ✅ Auth JWT
- ✅ Import Excel, export PDF/Excel

**Ce qui manque / doit évoluer :**
- ❌ Mono-mosquée → doit devenir multi-mosquée (django-tenants)
- ❌ URL ngrok/cloudflare tunnel → domaine propre nidham.fr
- ❌ Raspberry Pi → VPS Hetzner
- ❌ Pas de portail public/semi-public par mosquée
- ❌ Pas de rôles fin (Trésorier, Prof, Secrétaire)
- ❌ Pas de CI/CD GitHub Actions
- ❌ Pas de super-admin Nidham (vue cross-mosquées)

---

## 2. OÙ ON VEUT ALLER — VISION CIBLE

### 2.1 Vision produit

Nidham est une plateforme SaaS multi-tenant de gestion de mosquées.
Chaque mosquée cliente dispose de son propre espace isolé, accessible via un sous-domaine dédié sur nidham.fr.
Tu (Badreddine) es le super-admin de toute la plateforme.

### 2.2 Écosystème d'URLs cible

```
nidham.fr                     → Landing page publique (présentation Nidham)
app.nidham.fr                 → Portail de connexion général
{slug}.nidham.fr              → Espace privé de chaque mosquée (ex: lyonlpa.nidham.fr)
{slug}.nidham.fr/public       → Dashboard public (dons, KPIs, agenda) — sans login
{slug}.nidham.fr/tv           → Mode affichage kiosk (TV dans la mosquée)
admin.nidham.fr               → Super-admin Nidham (toutes les mosquées)
api.nidham.fr                 → API DRF (pour future app mobile)
```

### 2.3 Architecture multi-tenant choisie : Schema-per-Tenant

**Principe :** 1 seule base PostgreSQL, avec 1 schéma PostgreSQL par mosquée.
La librairie `django-tenants` gère automatiquement le routage vers le bon schéma
en fonction du sous-domaine détecté dans la requête HTTP.

```
Requête : lyonlpa.nidham.fr/api/school/students/
    ↓
Middleware django-tenants détecte "lyonlpa"
    ↓
Active le schéma PostgreSQL "lyonlpa"
    ↓
Toutes les requêtes Django utilisent UNIQUEMENT ce schéma
    ↓ 
0 risque de fuite vers une autre mosquée
```

**Schéma "public" (partagé) :** contient les tenants, domaines, plans, billing.
**Schémas mosquées :** contiennent toutes les tables métier (school, membership, treasury, kpi, core).

### 2.4 Rôles utilisateurs (RBAC étendu)

| Rôle | Code | Périmètre |
|------|------|-----------|
| Super Admin Nidham | `nidham_admin` | Toutes les mosquées |
| Directeur Mosquée | `mosque_director` | Toute sa mosquée |
| Trésorier | `treasurer` | Finances + lecture familles |
| Directeur École | `school_director` | Toutes les classes |
| Professeur | `teacher` | Sa classe uniquement |
| Secrétaire | `secretary` | Familles + inscriptions |
| Lecteur | `reader` | Lecture seule |

### 2.5 Portails publics par mosquée

Chaque mosquée peut activer/désactiver via son admin :
- Dashboard KPI public (dons collectés, objectifs waqf, nb familles)
- Agenda public (événements, horaires prières)
- Mode TV kiosk (URL dédiée pour affichage physique dans la mosquée)

---

## 3. ARCHITECTURE TECHNIQUE CIBLE

### 3.1 Schéma global

```
                      INTERNET
                          │
             ┌────────────▼────────────┐
             │      Cloudflare CDN      │
             │  SSL + DDoS + DNS        │
             │  *.nidham.fr → VPS IP    │
             └────────────┬────────────┘
                          │ HTTPS (443)
             ┌────────────▼────────────────────────────┐
             │        VPS Hetzner CX32                  │
             │        Ubuntu 24.04 LTS                  │
             │        4 vCPU / 8 GB RAM / 80 GB NVMe    │
             │        ~8€/mois — Falkenstein (DE)        │
             │                                          │
             │  ┌──────────────────────────────────┐    │
             │  │  Nginx (reverse proxy)            │    │
             │  │  + Certbot SSL (Let's Encrypt)    │    │
             │  │  lyonlpa.nidham.fr → :8000        │    │
             │  │  nidham.fr         → :3000 (landing)│  │
             │  └─────────────┬────────────────────┘    │
             │                │                         │
             │  ┌─────────────▼────────────────────┐    │
             │  │  Docker Compose (prod)             │    │
             │  │                                   │    │
             │  │  [backend-prod]                   │    │
             │  │  Gunicorn + Django 5.1.5           │    │
             │  │  django-tenants middleware         │    │
             │  │  port 8000                         │    │
             │  │                                   │    │
             │  │  [db]                             │    │
             │  │  PostgreSQL 16                    │    │
             │  │  schéma public : tenants/domaines │    │
             │  │  schéma lyonlpa : toutes les tables│   │
             │  │  schéma grenoble : toutes les tables│  │
             │  │  volume persistant /pg_data        │    │
             │  │                                   │    │
             │  │  [backup-cron]                    │    │
             │  │  pg_dump quotidien à 2h            │    │
             │  │  → Hetzner Object Storage (S3)    │    │
             │  └───────────────────────────────────┘    │
             └──────────────────────────────────────────┘
                          │
             ┌────────────▼────────────┐
             │     GitHub Actions       │
             │  push main → SSH VPS     │
             │  docker-compose up -d    │
             └─────────────────────────┘
```

### 3.2 Stack technique finale

| Composant | Technologie | Version | Notes |
|-----------|------------|---------|-------|
| Serveur | Hetzner CX32 | Ubuntu 24.04 LTS | Falkenstein DE |
| Reverse proxy | Nginx + Certbot | latest | SSL auto Let's Encrypt |
| App server | Gunicorn | 21.2.0 | déjà dans requirements.txt |
| Framework | Django | 5.1.5 | déjà installé |
| API | Django REST Framework | 3.15.2 | déjà installé |
| Multi-tenant | django-tenants | 3.6+ | À AJOUTER |
| Auth | djangorestframework-simplejwt | 5.3.1 | déjà installé |
| Base de données | PostgreSQL | 16 | déjà dans docker-compose |
| DNS/CDN | Cloudflare | Free | wildcard *.nidham.fr |
| Backups | pg_dump + Hetzner S3 | — | déjà le script, adapter la destination |
| CI/CD | GitHub Actions | — | À CRÉER |
| Containerisation | Docker + docker-compose | — | déjà en place |

---

## 4. CE QUI CHANGE TECHNIQUEMENT (DELTA)

### 4.1 Ajout de django-tenants (changement majeur)

**Installation :**
```bash
pip install django-tenants==3.6.1
```

**Modifications nécessaires dans le code existant :**

1. `requirements.txt` → ajouter `django-tenants==3.6.1`

2. `backend/config/settings.py` → modifier :
```python
INSTALLED_APPS = [
    "django_tenants",          # DOIT être en premier
    "core",                    # contient le modèle Tenant
    ...
]

DATABASE_ROUTERS = ("django_tenants.routers.TenantSyncRouter",)

TENANT_MODEL = "core.Mosque"           # modèle existant → devient Tenant
TENANT_DOMAIN_MODEL = "core.Domain"   # nouveau modèle à créer

# Apps partagées (schéma public)
SHARED_APPS = [
    "django_tenants",
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "core",                    # Mosque + Domain + User global
]

# Apps par mosquée (chaque schéma tenant)
TENANT_APPS = [
    "school",
    "membership", 
    "treasury",
    "kpi",
]
```

3. `backend/core/models.py` → modifier le modèle `Mosque` :
```python
from django_tenants.models import TenantMixin, DomainMixin

class Mosque(TenantMixin):          # était: models.Model
    name = models.CharField(...)
    # ... champs existants conservés ...
    auto_create_schema = True       # crée le schéma PG automatiquement

class Domain(DomainMixin):          # NOUVEAU modèle
    pass
```

4. `backend/config/wsgi.py` → remplacer WSGIHandler :
```python
from django_tenants.middleware.main import TenantMainMiddleware
# Le middleware détecte le sous-domaine → active le bon schéma
```

5. Migrations à relancer :
```bash
python manage.py migrate_schemas --shared   # schéma public
python manage.py create_tenant              # pour Lyon LPA existant
```

### 4.2 Migration des données existantes (Lyon LPA)

**Étapes pour migrer les données de la Raspberry Pi :**
```bash
# Sur la Raspberry Pi :
docker compose exec db pg_dump -U $POSTGRES_USER $POSTGRES_DB > dump_lyonlpa.sql

# Transférer vers le VPS :
scp dump_lyonlpa.sql user@VPS_IP:/home/user/

# Sur le VPS, après création du tenant lyonlpa :
docker compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB \
  -c "SET search_path TO lyonlpa;" \
  -f /home/user/dump_lyonlpa.sql
```

### 4.3 Nouveau fichier docker-compose.prod.yml

Remplace le profil `prod` actuel du docker-compose.yml.
**Différences clés par rapport à l'existant :**
- Supprimer le service `cloudflared` (plus besoin, Nginx gère le SSL via Certbot)
- Ajouter `DJANGO_SETTINGS_MODULE=config.settings_prod`
- Volumes backups → pointer vers bucket Hetzner S3 (via rclone ou boto3)
- Gunicorn : augmenter à 4 workers sur CX32

### 4.4 Config Nginx pour wildcard nidham.fr

```nginx
# /etc/nginx/sites-available/nidham
server {
    listen 443 ssl;
    server_name *.nidham.fr nidham.fr;

    ssl_certificate     /etc/letsencrypt/live/nidham.fr/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/nidham.fr/privkey.pem;

    location /static/ {
        alias /app/staticfiles/;
    }

    location / {
        proxy_pass         http://localhost:8000;
        proxy_set_header   Host $host;              # CRITIQUE pour django-tenants
        proxy_set_header   X-Real-IP $remote_addr;
    }
}
```
> **Important :** `proxy_set_header Host $host` est obligatoire pour que django-tenants détecte correctement le sous-domaine.

**Certificat wildcard via Certbot + Cloudflare DNS challenge :**
```bash
certbot certonly --dns-cloudflare \
  --dns-cloudflare-credentials ~/.cloudflare.ini \
  -d nidham.fr -d *.nidham.fr
```

### 4.5 GitHub Actions CI/CD (nouveau fichier)

Fichier : `.github/workflows/deploy.yml`
```yaml
name: Deploy to Hetzner VPS
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USER }}
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            cd /opt/nidham
            git pull origin main
            docker compose -f docker-compose.prod.yml build backend-prod
            docker compose -f docker-compose.prod.yml up -d --no-deps backend-prod
            docker compose exec backend-prod python manage.py migrate_schemas
            docker compose exec backend-prod python manage.py collectstatic --noinput
```

---

## 5. RÔLES RBAC — MODÈLE DE DONNÉES ÉTENDU

Le `middleware.py` actuel gère un RBAC basique.
Il faut l'étendre pour supporter les rôles suivants :

```python
# backend/core/models.py — à ajouter

class UserRole(models.TextChoices):
    NIDHAM_ADMIN    = "nidham_admin",    "Super Admin Nidham"
    DIRECTOR        = "mosque_director", "Directeur Mosquée"
    TREASURER       = "treasurer",       "Trésorier"
    SCHOOL_DIRECTOR = "school_director", "Directeur École"
    TEACHER         = "teacher",         "Professeur"
    SECRETARY       = "secretary",       "Secrétaire"
    READER          = "reader",          "Lecteur"

class CustomUser(AbstractUser):          # modèle existant
    role = models.CharField(
        max_length=30,
        choices=UserRole.choices,
        default=UserRole.READER
    )
    class_scope = models.ForeignKey(     # NOUVEAU — pour les profs
        "school.SchoolClass",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        help_text="Classe assignée (profs uniquement)"
    )
```

---

## 6. PORTAIL PUBLIC — MODÈLE DE DONNÉES

```python
# backend/core/models.py — à ajouter dans MosqueSettings

class MosquePublicSettings(models.Model):
    mosque = models.OneToOneField(Mosque, on_delete=models.CASCADE)

    # Toggles publics
    show_donation_kpi     = models.BooleanField(default=False)
    show_family_count     = models.BooleanField(default=False)
    show_school_stats     = models.BooleanField(default=False)
    show_public_agenda    = models.BooleanField(default=False)
    show_waqf_progress    = models.BooleanField(default=False)

    # Objectifs affichables
    waqf_goal_amount      = models.DecimalField(null=True, blank=True, ...)
    waqf_goal_label       = models.CharField(max_length=200, blank=True)

    # Mode TV
    tv_mode_enabled       = models.BooleanField(default=False)
    tv_refresh_seconds    = models.IntegerField(default=30)
```

---

## 7. COÛTS MENSUELS (récapitulatif)

| Service | Détail | Coût/mois |
|---------|--------|-----------|
| VPS Hetzner CX32 | 4 vCPU, 8 GB RAM, 80 GB NVMe, Falkenstein DE | ~8€ |
| Hetzner Backups | Snapshots auto hebdomadaires (+20%) | ~1.6€ |
| Hetzner Object Storage | pg_dump quotidiens, 10 GB | ~1€ |
| Cloudflare | DNS + SSL + CDN | 0€ (Free) |
| Let's Encrypt | SSL wildcard *.nidham.fr | 0€ |
| GitHub Actions | CI/CD (2000 min/mois offerts) | 0€ |
| **TOTAL** | **Infrastructure complète, pro, multi-mosquée** | **~11€/mois** |

Scalabilité :
- 1-5 mosquées   → CX22 (~5€/mois)
- 5-20 mosquées  → CX32 (~9€/mois) ← on démarre ici
- 20-100 mosquées → CX42 (~17€/mois)
- 100+ mosquées  → CCX23 dédié (~50€/mois)

---

## 8. PLAN DE MIGRATION — ÉTAPES ORDONNÉES

### Phase 1 — Infra VPS (sans toucher au code)
1. Créer compte Hetzner + commander VPS CX32 (Ubuntu 24.04, Falkenstein)
2. Configurer SSH + firewall (ports 22, 80, 443 uniquement)
3. Installer Docker + Docker Compose sur le VPS
4. Pointer DNS Cloudflare : `A *.nidham.fr → IP VPS` + `A nidham.fr → IP VPS`
5. Installer Certbot + générer certificat wildcard `*.nidham.fr`
6. Configurer Nginx avec la config wildcard ci-dessus

### Phase 2 — Migration mono-mosquée (Lyon LPA, sans multi-tenant)
7. Cloner le repo sur le VPS : `git clone https://github.com/BadreddineEK/MManager`
8. Créer `.env` de prod (DEBUG=False, ALLOWED_HOSTS=*.nidham.fr, etc.)
9. Créer `docker-compose.prod.yml` sans cloudflared
10. `docker compose -f docker-compose.prod.yml up -d`
11. Dump BDD depuis Raspberry Pi + restore sur VPS
12. Tester sur `lyonlpa.nidham.fr` → si OK, couper la Raspberry Pi

### Phase 3 — Intégration django-tenants (multi-mosquée)
13. Ajouter `django-tenants` dans requirements.txt
14. Modifier `settings.py` : SHARED_APPS, TENANT_APPS, TENANT_MODEL
15. Modifier `core/models.py` : Mosque hérite TenantMixin, créer Domain
16. `python manage.py migrate_schemas --shared`
17. `python manage.py create_tenant --slug=lyonlpa --domain=lyonlpa.nidham.fr`
18. Re-importer les données de Lyon LPA dans le schéma `lyonlpa`
19. Tester isolation : créer une 2ème mosquée test, vérifier que les données ne se mélangent pas

### Phase 4 — CI/CD + Rôles + Portail public
20. Créer `.github/workflows/deploy.yml`
21. Ajouter secrets GitHub : VPS_HOST, VPS_USER, VPS_SSH_KEY
22. Étendre le modèle User avec les nouveaux rôles
23. Créer MosquePublicSettings
24. Créer les vues publiques (`/{slug}/public`, `/{slug}/tv`)

---

## 9. POINTS D'ATTENTION POUR COPILOT

### Ne pas casser :
- La logique d'import Excel existante (import_views.py — 30 KB de code)
- Le système de backup (backup_views.py + scripts/)
- Les tests existants (conftest.py, tests.py, tests_import.py)
- Le middleware RBAC existant (middleware.py) — l'étendre, ne pas le réécrire

### Points délicats de la migration django-tenants :
- `migrate_schemas` doit être utilisé à la place de `migrate` pour toutes les opérations de migration
- Le schéma `public` ne contient QUE les SHARED_APPS — ne pas mettre school/membership/treasury/kpi dedans
- Le `proxy_set_header Host $host` dans Nginx est OBLIGATOIRE
- Les tests existants doivent être adaptés pour utiliser `TenantTestCase` au lieu de `TestCase`
- Les fixtures et données de test doivent préciser dans quel schéma elles s'exécutent

### Variables d'environnement à ajouter pour la prod :
```
DEBUG=False
SECRET_KEY=<générer une nouvelle clé>
ALLOWED_HOSTS=.nidham.fr
DJANGO_SETTINGS_MODULE=config.settings_prod
POSTGRES_DB=nidham_prod
POSTGRES_USER=nidham
POSTGRES_PASSWORD=<strong password>
EMAIL_HOST=<SMTP provider>
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...
HETZNER_S3_BUCKET=nidham-backups
HETZNER_S3_ACCESS_KEY=...
HETZNER_S3_SECRET_KEY=...
```

---

## 10. FORMAT DE RAPPORT COPILOT (à coller ici régulièrement)

```
## Copilot Status — [DATE]
### Phase en cours : [1/2/3/4]
### Étape : [numéro et titre]
### Statut : ✅ Terminé / 🔄 En cours / ❌ Bloqué
### Fichiers modifiés :
- path/to/file.py
### Tests passés : oui/non
### Prochaine étape : ...
### Blocages / questions : ...
```
