# NIDHAM — CAHIER DES CHARGES COMPLET
## Plateforme SaaS de gestion de mosquées
### Version 2.0 — Avril 2026
### Repo : github.com/BadreddineEK/MManager

---

## 1. VISION & POSITIONNEMENT

### 1.1 Vision

Nidham est la première plateforme SaaS francophone dédiée à la gestion complète des mosquées et associations cultuelles musulmanes. Elle couvre l'administration, l'école coranique, la trésorerie, les adhérents, la communication et la transparence communautaire — dans un seul outil, accessible sans compétence technique.

### 1.2 Problème adressé

Les mosquées françaises gèrent aujourd'hui leurs données sur :
- Des fichiers Excel non sécurisés et non partageables
- Des logiciels associatifs génériques (HelloAsso, Assoconnect) non adaptés au culte
- Des outils anglais (ConnectMazjid, Masjid.io) sans traduction ni conformité RGPD française
- Des solutions sur mesure coûteuses et non maintenables

Nidham répond à ce manque avec un outil pensé pour les mosquées francophones, conforme RGPD, hébergé en Europe, et adapté aux réalités associatives (loi 1901/1905, reçus fiscaux, waqf).

### 1.3 Marché cible

- **Primaire** : Mosquées françaises (estimées 2 500+ en France)
- **Secondaire** : Belgique, Suisse, Maroc (francophone)
- **Niche initiale** : Mosquées de taille moyenne (100-500 familles), région Auvergne-Rhône-Alpes en premier

### 1.4 Positionnement

> "Nidham, c'est le logiciel de gestion qu'une mosquée mérite — simple, complet, sécurisé, et fait par quelqu'un qui comprend vos besoins."

---

## 2. LES 3 PRODUITS NIDHAM

Nidham existe en 3 formes distinctes selon le niveau d'autonomie et de budget de la mosquée.

### 2.1 Nidham Self-Hosted (gratuit, code open-source)

**Principe** : La mosquée héberge elle-même l'application sur sa propre infrastructure (Raspberry Pi, NAS, serveur associatif, VPS personnel).

**Public cible** : Mosquées tech-friendly, bénévoles avec compétences informatiques, mosquées soucieuses de souveraineté totale de leurs données.

**Ce qui est inclus** : Le code complet du core (voir section Modules), documentation d'installation, docker-compose prêt à l'emploi.

**Ce qui N'est PAS inclus** : Hébergement, support, modules avancés (école complète, SMS, app mobile, portail public).

**Modèle économique** : Gratuit. Rôle d'acquisition et de réputation. Pas de coût d'infra pour Nidham.

**Livraison** : GitHub public (ou accès sur demande), documentation INSTALL.md.

---

### 2.2 Nidham Cloud Free (gratuit, hébergé par Nidham)

**Principe** : La mosquée accède à Nidham via `{slug}.nidham.fr` sans aucune installation. Nidham héberge et maintient.

**Disponibilité** : Lancé uniquement quand les abonnements Pro couvrent les coûts d'infra (objectif : 5+ mosquées payantes avant activation).

**Limites** :
- 1 admin uniquement
- Max 75 familles / 150 élèves
- Core uniquement (pas de modules avancés)
- Backups 1x/semaine (vs quotidien en Pro)
- Support : documentation uniquement

**Objectif** : Outil d'acquisition — une mosquée free bien onboardée devient payante dans 3-6 mois ou recommande à d'autres.

---

### 2.3 Nidham Cloud Pro (payant, hébergé par Nidham)

**Principe** : Abonnement mensuel, accès à tout ou partie des modules selon le plan choisi.

**Accès** : `{slug}.nidham.fr` avec sous-domaine dédié, SSL, backups quotidiens, support.

**Plans** : voir section 4.

---

## 3. MODULES & FONCTIONNALITÉS

### MODULE 0 — CORE (inclus dans tous les plans)

**Gestion des familles & adhérents**
- Fiche famille complète (chef de famille, conjoint, enfants, adresse, contact)
- Statut d'adhésion (actif, expiré, en attente)
- Import familles depuis Excel (colonnes configurables)
- Export Excel + PDF liste adhérents
- Filtre impayés cotisations
- Historique des modifications (audit log)

**Trésorerie basique**
- Saisie manuelle entrées/sorties
- Catégories configurables (don, loyer, facture, cotisation, projet…)
- Import relevés bancaires CSV (Crédit Agricole, BNP, Banque Populaire)
- Dispatch automatique par mots-clés (règles configurables)
- Solde en temps réel
- Export Excel mensuel/annuel

**Paramètres mosquée**
- Nom, adresse, logo, régime fiscal (1901/1905)
- Année scolaire active
- Tarifs école et cotisations
- Configuration SMTP email (notifications)
- Gestion des comptes bancaires

**Administration & sécurité**
- Auth JWT sécurisée
- 1 à N admins selon le plan
- Audit log de toutes les actions sensibles
- Backup manuel depuis l'interface

---

### MODULE 1 — ÉCOLE CORANIQUE (payant)

*Fonctionnalité Pronote-like pour l'école coranique de la mosquée.*

**Gestion des classes**
- Création de classes par niveau (NP, N1, N2… configurable)
- Affectation d'un ou plusieurs professeurs par classe
- Liste des élèves par classe avec fiche individuelle

**Appel & présences**
- Interface appel simplifiée (1 clic par élève : présent/absent/retard)
- Historique des présences par élève
- Taux d'assiduité calculé automatiquement
- Alerte automatique au bout de N absences consécutives (configurable)

**Suivi pédagogique**
- Suivi de mémorisation Coran (sourates acquises, en cours, à réviser)
- Appréciations par période
- Bulletins PDF générés automatiquement (logo mosquée, niveau, absences, progression Coran, appréciation)

**Espace Professeur (login dédié)**
- Chaque prof a son propre compte limité à sa classe
- Accès appel, suivi élèves, messagerie parents de SA classe uniquement
- Envoi d'email groupé aux parents de la classe

**Gestion financière école**
- Suivi des frais de scolarité par élève
- Statut paiement (payé, partiel, impayé)
- Relance automatique (email) des impayés
- Reçus de paiement PDF

---

### MODULE 2 — PORTAIL ADHÉRENTS (payant)

*Espace connecté pour les familles membres de la mosquée.*

**Accès famille**
- Chaque famille reçoit des identifiants de connexion
- Tableau de bord personnel : cotisations, dons, reçus fiscaux
- Téléchargement des reçus fiscaux PDF directement

**Renouvellement en ligne**
- Formulaire de renouvellement d'adhésion
- Paiement en ligne (Stripe ou HelloAsso)
- Confirmation automatique par email

**Historique**
- Liste de tous les dons et cotisations de la famille
- Reçus fiscaux archivés (5 ans)

---

### MODULE 3 — COMMUNICATION & RELANCES (payant)

*Outils de communication automatisée entre la mosquée et ses membres.*

**Email**
- Envoi groupé par segment (tous adhérents, parents d'élèves d'une classe, impayés…)
- Templates personnalisables avec variables (prénom, montant dû, nom mosquée…)
- Envoi depuis l'adresse SMTP de la mosquée (configurée dans les paramètres)
- Historique des envois

**SMS (via Twilio ou Brevo)**
- Relances SMS automatiques pour impayés cotisations et école
- Rappels événements importants
- Crédit SMS inclus selon le plan (ex: 100 SMS/mois en Pro)

**Notifications automatiques**
- Email automatique à chaque nouveau paiement enregistré
- Rappel renouvellement adhésion (J-30, J-7, J+7)
- Résumé mensuel envoyé aux admins (trésorerie, école)
- Alerte impayés hebdomadaire

---

### MODULE 4 — PORTAIL PUBLIC & TV (payant)

*Vitrine publique de la mosquée et affichage en temps réel.*

**Dashboard public** (`{slug}.nidham.fr/public`)
- KPIs configurables : dons collectés ce mois, objectif waqf, nombre d'adhérents, nb d'élèves
- Projets de financement participatif (barre de progression style crowdfunding)
- Agenda public (événements, horaires prières)
- Entièrement configurable : la mosquée choisit ce qui est visible

**Mode TV kiosk** (`{slug}.nidham.fr/tv`)
- URL dédiée pour affichage sur écran dans la mosquée (sans login)
- Rafraîchissement automatique configurable (30s, 60s…)
- Design épuré plein écran, adapté aux grands écrans
- Affichage : prochaine prière, annonces, KPIs sélectionnés, agenda

**Agenda public**
- Événements visibles publiquement (cours, conférences, collectes)
- Affichage calendrier ou liste
- Iframes intégrables sur d'autres sites

---

### MODULE 5 — ANALYTICS & RAPPORTS (payant)

*Business intelligence et reporting automatisé pour les responsables.*

**KPIs croisés**
- Vue dashboard admin : école + trésorerie + adhésions en un coup d'œil
- Évolution mensuelle sur 12 mois (graphiques)
- Comparaison N / N-1

**Exports avancés**
- Export FEC (Fichier d'Écriture Comptable) pour expert-comptable
- Rapport PDF mensuel auto-généré (envoyé au trésorier)
- Export données brutes par module (familles, paiements, élèves…)

**Projections**
- Projection trésorerie sur 3 mois (tendance)
- Taux de renouvellement adhésions
- Taux de remplissage école par niveau

---

### MODULE 6 — APP MOBILE (payant, inclus en Premium)

*Application mobile pour admins et parents.*

**App Parents**
- Consulter absences de leur(s) enfant(s)
- Voir et télécharger les bulletins
- Payer les frais de scolarité
- Recevoir les notifications push (absence, bulletin disponible, événement)

**App Admin (version légère)**
- Tableau de bord KPIs
- Appel rapide (présences)
- Voir liste des impayés

**Stack** : React Native (iOS + Android depuis 1 codebase) ou PWA progressive selon budget.

---

### MODULE 7 — MULTI-SITES / FÉDÉRATION (sur devis)

*Pour les fédérations gérant plusieurs mosquées.*

- 1 compte Nidham pour N mosquées
- Dashboard fédéral (KPIs agrégés de toutes les mosquées)
- Facturation centralisée
- Gestion des accès par site
- Rapports consolidés (idéal pour les UOIF, fédérations régionales)

---

## 4. PLANS TARIFAIRES

### Nidham Self-Hosted — Gratuit
- Code open-source
- Core complet
- Installation manuelle (Pi, serveur)
- 0€ / Pas de support

### Nidham Cloud Free — Gratuit
- Hébergé par Nidham
- Core limité (75 familles, 150 élèves max, 1 admin)
- `{slug}.nidham.fr`
- Support : doc uniquement
- Disponible après 5 mosquées payantes

### Nidham Starter — 19€/mois (ou 190€/an = 2 mois offerts)
- Core complet (illimité)
- 3 admins
- 1 module au choix (École OU Communication)
- Backups quotidiens
- Support email (48h)

### Nidham Pro — 49€/mois (ou 490€/an)
- Core complet
- 10 users (tous rôles)
- Modules : École + Communication + Portail Public & TV
- Analytics basiques
- 200 SMS/mois inclus
- Support email prioritaire (24h)

### Nidham Premium — 89€/mois (ou 890€/an)
- Core complet
- Users illimités
- Tous les modules inclus (École, Communication, Portail, Analytics, App Mobile)
- 500 SMS/mois inclus
- Support chat + téléphone
- Onboarding personnalisé (1h de formation incluse)

### Nidham Fédération — Sur devis
- Multi-sites
- Dashboard fédéral
- Facturation centralisée
- SLA garanti

---

## 5. ARCHITECTURE TECHNIQUE

### 5.1 Stack

| Composant | Technologie | Notes |
|-----------|------------|-------|
| Backend | Django 5.1.5 + DRF | Existant dans le repo |
| Multi-tenant | django-tenants | Schéma PostgreSQL par mosquée |
| Auth | JWT (simplejwt) | Existant |
| Base de données | PostgreSQL 16 | Docker |
| Reverse proxy | Nginx + Certbot | SSL wildcard *.nidham.fr |
| App server | Gunicorn | Existant |
| Hébergement | Hetzner CX32 (VPS) | Falkenstein DE, RGPD |
| DNS / CDN | Cloudflare | Wildcard *.nidham.fr |
| Backups | pg_dump → Hetzner S3 | Quotidien |
| CI/CD | GitHub Actions | Push → deploy auto |
| SMS | Brevo ou Twilio | API |
| Paiement | Stripe + HelloAsso | Pour portail adhérents |
| App mobile | React Native / PWA | Phase 2 |

### 5.2 Architecture Multi-tenant

Schéma PostgreSQL par mosquée (django-tenants, Schema-per-tenant).

```
schéma public   → tenants, domaines, plans, subscriptions, billing
schéma lyonlpa  → families, students, payments, treasury, kpi…
schéma grenoble → families, students, payments, treasury, kpi…
```

Chaque mosquée accède via son sous-domaine :
`{slug}.nidham.fr` → détecté par le middleware django-tenants → activation du bon schéma.

### 5.3 Modèle de données — Schéma Public (partagé)

```python
# Schéma public — modèles partagés entre tous les tenants

class Mosque(TenantMixin):          # hérite TenantMixin (django-tenants)
    name = CharField()
    slug = SlugField(unique=True)
    timezone = CharField()
    plan = ForeignKey(Plan)
    subscription = OneToOneField(Subscription)
    created_at = DateTimeField()
    auto_create_schema = True

class Domain(DomainMixin):          # sous-domaine nidham.fr
    pass

class Plan(Model):
    name = CharField()              # "free", "starter", "pro", "premium"
    price_monthly = DecimalField()
    price_yearly = DecimalField()
    max_families = IntegerField()   # -1 = illimité
    max_users = IntegerField()
    max_sms_month = IntegerField()
    modules = JSONField()           # ["core", "school", "communication", ...]

class Subscription(Model):
    mosque = OneToOneField(Mosque)
    plan = ForeignKey(Plan)
    status = CharField()            # "active", "trial", "expired", "cancelled"
    billing_cycle = CharField()     # "monthly", "yearly"
    current_period_start = DateField()
    current_period_end = DateField()
    stripe_subscription_id = CharField(null=True)
    helloasso_subscription_id = CharField(null=True)
```

### 5.4 Middleware de limites (Plan Enforcement)

```python
# Vérifie avant chaque action si la mosquée a le droit selon son plan

class PlanEnforcementMiddleware:
    def check_module(self, request, module_name):
        # Si le module n'est pas dans le plan → 403 avec message d'upgrade
        plan = request.tenant.subscription.plan
        if module_name not in plan.modules:
            raise PermissionDenied("Module non inclus dans votre plan")

    def check_limit(self, request, resource, current_count):
        # Si limite atteinte → 403 avec message d'upgrade
        plan = request.tenant.subscription.plan
        limit = getattr(plan, f"max_{resource}")
        if limit != -1 and current_count >= limit:
            raise PermissionDenied(f"Limite {resource} atteinte. Passez au plan supérieur.")
```

### 5.5 URLs de l'écosystème

```
nidham.fr                    → Landing page (Vercel ou VPS)
app.nidham.fr                → Portail connexion général
{slug}.nidham.fr             → App privée de chaque mosquée
{slug}.nidham.fr/public      → Dashboard public (sans login)
{slug}.nidham.fr/tv          → Mode kiosk TV (sans login)
admin.nidham.fr              → Super-admin Nidham (toi)
api.nidham.fr                → API DRF (app mobile future)
```

### 5.6 RBAC — Rôles utilisateurs

| Rôle | Code | Périmètre |
|------|------|-----------|
| Super Admin Nidham | nidham_admin | Toutes les mosquées (toi) |
| Directeur Mosquée | mosque_director | Tout dans sa mosquée |
| Trésorier | treasurer | Finances + lecture familles |
| Directeur École | school_director | Toutes les classes |
| Professeur | teacher | Sa classe uniquement |
| Secrétaire | secretary | Familles + inscriptions |
| Lecteur | reader | Lecture seule |

---

## 6. RGPD & SÉCURITÉ

- Hébergement 100% Europe (Hetzner DE) → conformité RGPD native
- Chaque mosquée = schéma isolé → impossible pour une mosquée d'accéder aux données d'une autre
- Données sensibles (mots de passe SMTP, IBAN) chiffrées en base
- Audit log immuable de toutes les actions (déjà implémenté)
- Politique de rétention : données supprimées 30 jours après résiliation
- Export complet des données sur demande (droit à la portabilité RGPD)
- Backups quotidiens chiffrés (pg_dump AES-256)
- SSL TLS 1.3 sur tous les sous-domaines (wildcard Let's Encrypt via Cloudflare)

---

## 7. ROADMAP DE DÉVELOPPEMENT

### Phase 0 — En cours (Raspberry Pi, 1 mosquée) ✅ FAIT
- Core complet fonctionnel (familles, trésorerie, école basique, exports PDF/Excel)
- Auth JWT + RBAC
- Docker Compose + backup cron
- Validation terrain avec Lyon LPA

### Phase 1 — Migration Multi-Tenant (Raspberry Pi, test 2-3 mosquées)
- Intégrer django-tenants
- Schéma par mosquée
- Rôles étendus (Trésorier, Prof, Secrétaire)
- Tests isolation données
- Simuler sous-domaines en local (/etc/hosts)
- Valider avec 2-3 mosquées en Self-Hosted

### Phase 2 — Lancement VPS + Core SaaS
- Commander Hetzner CX32
- Déployer sur VPS avec domaine nidham.fr
- Modèles Plan + Subscription
- Middleware de limites
- Onboarder 5 premières mosquées (gratuites) pour validation
- CI/CD GitHub Actions

### Phase 3 — Module École complet
- Espace professeur avec login dédié
- Appel / présences
- Suivi Coran individualisé
- Bulletins PDF
- Relances email parents

### Phase 4 — Module Communication & Portail Public
- Envoi email groupé par segment
- Intégration SMS (Brevo)
- Dashboard public {slug}.nidham.fr/public
- Mode TV kiosk

### Phase 5 — Facturation & Portail Adhérents
- Intégration Stripe + HelloAsso
- Plans payants actifs
- Portail famille (espace connecté)
- Renouvellement adhésion en ligne

### Phase 6 — Analytics & App Mobile
- KPIs croisés + exports FEC
- PWA ou React Native
- App parents (absences, bulletins, paiements)

### Phase 7 — Fédérations & International
- Dashboard multi-sites
- Support arabe / anglais
- Expansion Belgique, Maroc

---

## 8. PROJECTIONS ÉCONOMIQUES

### Coûts d'infrastructure selon la croissance

| Nb mosquées Cloud | VPS recommandé | Coût infra/mois |
|-------------------|---------------|-----------------|
| 1-5 | Hetzner CX22 | ~5€ |
| 5-20 | Hetzner CX32 | ~11€ |
| 20-50 | Hetzner CX42 | ~20€ |
| 50-200 | Hetzner CCX23 (dédié) | ~55€ |

### Scénarios de revenus

**Scénario conservateur (12 mois) :**
- 30 Self-Hosted (gratuit) → 0€ mais bouche à oreille
- 10 Free Cloud → 0€
- 8 Starter (19€) → 152€/mois
- 5 Pro (49€) → 245€/mois
- 2 Premium (89€) → 178€/mois
- **MRR : 575€ | Coût infra : ~20€ | Marge : 97%**

**Scénario optimiste (18 mois) :**
- 20 Starter → 380€/mois
- 15 Pro → 735€/mois
- 8 Premium → 712€/mois
- 2 Fédération → 500€/mois
- **MRR : 2 327€ | Coût infra : ~55€ | Marge : 98%**

---

## 9. STRATÉGIE D'ACQUISITION

### Canal 1 — Bouche à oreille inter-mosquées (principal)
Les responsables de mosquées se connaissent et se parlent (fédérations, formations, réseaux locaux). 1 mosquée satisfaite = 3-5 recommandations potentielles.

**Action** : Soigner l'onboarding de Lyon LPA, leur donner des "codes de parrainage" pour inviter d'autres mosquées.

### Canal 2 — GitHub & communauté dev musulmane
Repo open-source bien documenté → devs bénévoles dans les mosquées trouvent Nidham, l'installent, parlent du Cloud payant.

### Canal 3 — LinkedIn & contenu
Posts LinkedIn sur la gestion associative, la transparence financière, la digitalisation des mosquées. Cas client anonymisé (KPIs réels).

### Canal 4 — Fédérations islamiques
Contacter les fédérations (UOIF, FNMF, Rassemblement Musulman de France) pour un partenariat ou référencement officiel. 1 accord avec une fédération = accès à des centaines de mosquées.

---

## 10. POINTS D'ATTENTION POUR COPILOT

### Ne pas casser (code existant à préserver) :
- import_views.py (logique import Excel complexe, 30 KB)
- backup_views.py + scripts/backup.sh
- notification_views.py (SMTP)
- export_views.py (PDF ReportLab + Excel)
- Tous les tests existants (adapter pour TenantTestCase)

### Ordre strict de développement à respecter :
1. django-tenants AVANT tout nouveau feature
2. Plan + Subscription AVANT le middleware de limites
3. Middleware de limites AVANT l'activation des modules payants
4. Tests d'isolation tenant AVANT tout déploiement cloud

### Variables d'environnement à ajouter :
```
STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
STRIPE_WEBHOOK_SECRET=
BREVO_API_KEY=
HETZNER_S3_BUCKET=nidham-backups
HETZNER_S3_ENDPOINT=https://fsn1.your-objectstorage.com
HETZNER_S3_ACCESS_KEY=
HETZNER_S3_SECRET_KEY=
```

---

## 11. FORMAT DE RAPPORT COPILOT

À coller ici après chaque session de travail :

```
## Copilot Status — [DATE]
Phase : [0/1/2/3/4/5/6/7]
Étape : [titre]
Statut : ✅ Terminé / 🔄 En cours / ❌ Bloqué
Fichiers modifiés :
- path/to/file.py
Tests : ✅ passés / ❌ échoués
Prochaine étape :
Blocages / questions :
```
