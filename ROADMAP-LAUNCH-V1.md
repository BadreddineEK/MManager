# 🚀 Mosquée Manager — Roadmap Lancement V1 (SaaS)

> **Objectif :** Passer d'un outil fonctionnel auto-hébergé à un vrai produit SaaS commercialisable, stable, sécurisé et prêt à facturer.  
> **Périmètre :** Fonctionnalités existantes parfaites — AUCUNE nouvelle feature avant que tout soit solide.  
> **Dernière mise à jour :** 23 avril 2026

---

## 🗺️ Vue d'ensemble des phases

| Phase | Nom | Priorité | Estimation |
|-------|-----|----------|------------|
| **P1** | Stabilisation & bugs | 🔴 Critique | 1–2 semaines |
| **P2** | Sécurité & conformité RGPD | 🔴 Critique | 1 semaine |
| **P3** | Infrastructure cloud & CI/CD | 🔴 Critique | 1 semaine |
| **P4** | Onboarding automatisé | 🟠 Important | 1–2 semaines |
| **P5** | Monétisation & billing | 🟠 Important | 1–2 semaines |
| **P6** | UX/UI polish | 🟡 Nécessaire | 1 semaine |
| **P7** | Légal & documentation | 🟡 Nécessaire | 3–5 jours |
| **P8** | Support client & monitoring | 🟢 Avant lancement | 3–5 jours |

---

## P1 — Stabilisation & correction de bugs 🔴

> Tout ce qui existe doit fonctionner sans bug avant de le vendre.

### 1.1 Tests & couverture

- [ ] **Audit complet des 160 tests** — s'assurer qu'ils couvrent tous les edge cases critiques
- [ ] **Tests manquants identifiés à ajouter :**
  - [ ] `user_views.py` — tests RBAC (non-ADMIN ne peut pas modifier un user)
  - [ ] `user_views.py` — test auto-suppression bloquée
  - [ ] Reçus PDF école & cotisations — test génération (mock weasyprint)
  - [ ] `settings.py` API — test update partiel
  - [ ] Notifications email — test envoi (mock SMTP)
  - [ ] Import Excel — test fichier malformé / colonnes manquantes
- [ ] **Tests end-to-end** avec données réelles anonymisées (1 passage complet : onboarding → import → paiements → reçu PDF)
- [ ] **Objectif couverture :** ≥ 85% sur les apps `core`, `school`, `membership`, `treasury`

### 1.2 Bugs connus / non testés depuis l'UI

- [ ] **Gestion utilisateurs (UI)** — tester le modal création/édition depuis navigateur
  - [ ] Création user : vérifier username_display (sans prefix schema)
  - [ ] Édition user : champ password vide = pas de changement
  - [ ] Reset MDP depuis modal
  - [ ] Suppression avec confirmation
  - [ ] RBAC : non-ADMIN ne voit pas la section "Utilisateurs"
- [ ] **Reçus PDF école** — bouton 🧾 → téléchargement PDF réel (test sur Pi)
- [ ] **Reçus PDF cotisations** — idem
- [ ] **Import Excel** — tester avec fichier réel (école + cotisations)
- [ ] **Export CSV** — vérifier encodage UTF-8 (prénoms arabes / accents)
- [ ] **Cloudflare Tunnel** — `mmanager-cloudflared-1` en `Restarting (255)` → **fix obligatoire avant lancement**
- [ ] **Panneau Paramètres** — tester modification depuis UI (tarifs, niveaux école)
- [ ] **KPI screen** — auto-refresh 30s sur écran TV, vérifier absence de PII
- [ ] **Session expirée** — vérifier que le frontend redirige proprement vers login (refresh token + fallback)

### 1.3 Validation données & erreurs

- [ ] **Messages d'erreur API** — vérifier que les 400/403/404/500 retournent des messages lisibles (pas de traceback Django brut)
- [ ] **Validation frontend** — champs obligatoires, formats (email, montant, date) avant envoi API
- [ ] **Gestion doublons** — Family + Child : que se passe-t-il si même nom/tel déjà présent ?
- [ ] **Montants négatifs** — bloquer côté API + UI
- [ ] **Suppression en cascade** — tester : supprimer une famille → que deviennent les enfants et paiements ?

---

## P2 — Sécurité & conformité RGPD 🔴

### 2.1 Sécurité applicative

- [ ] **Rate limiting** sur login (`/api/auth/login/`) — max 5 tentatives / 5 min par IP
- [ ] **CORS restrictif** — `CORS_ALLOWED_ORIGINS` strictement configuré (pas de `*`)
- [ ] **Headers HTTP sécurité** — `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`, `Content-Security-Policy` via Nginx
- [ ] **JWT refresh rotation** — invalider l'ancien refresh token à chaque renouvellement
- [ ] **Audit log complet** — vérifier que TOUTES les actions sensibles sont loggées (import, export, suppression, reset MDP)
- [ ] **Validation côté serveur stricte** — aucune confiance aux données frontend
- [ ] **SECRET_KEY forte** — vérifier que `.env.example` ne contient pas de vraie clé, rotation documentée
- [ ] **Mots de passe** — politique minimum : 8 chars, 1 maj, 1 chiffre (déjà `Admin1234!` mais à enforcer côté API)
- [ ] **Chiffrement backups** — valider AES-256 sur nouvelle instance (déjà testé en dev, valider prod)

### 2.2 RGPD / données personnelles

- [ ] **Politique de confidentialité** — rédiger un document simple décrivant les données collectées (noms, emails, tél), durée conservation, droits
- [ ] **Droit à l'effacement** — endpoint `DELETE /api/users/<id>/` existe → s'assurer que toutes les données liées sont effacées ou anonymisées
- [ ] **Portabilité** — export CSV existant = suffisant MVP, documenter
- [ ] **Consentement** — lors de l'onboarding mosquée, acceptation explicite des CGU + politique de confidentialité
- [ ] **Hébergement EU** — si cloud, choisir Hetzner/OVH EU (pas AWS us-east) pour conformité RGPD
- [ ] **Durée de conservation** — politique claire dans les paramètres (ex: purger les données > 5 ans automatiquement, ou informer l'admin)
- [ ] **Données de logging** — ne pas loguer les mots de passe ni les données perso dans les logs Django

### 2.3 Isolation multi-tenant

- [ ] **Audit isolation** — vérifier que CHAQUE endpoint filtre bien par `mosque_id` (aucune fuite cross-tenant)
- [ ] **Test isolation** — créer 2 tenants en test et vérifier qu'un user A ne peut pas voir les données de B
- [ ] **Superuser Django** — documenter qu'il n'a pas accès aux données applicatives (uniquement admin Django)

---

## P3 — Infrastructure cloud & CI/CD 🔴

### 3.1 Domaine & SSL

- [ ] **Nom de domaine** — acheter `mosqueemanager.fr` (ou `.com`) + sous-domaines `app.mosqueemanager.fr`, `api.mosqueemanager.fr`
- [ ] **SSL/TLS automatique** — Let's Encrypt via Traefik ou Nginx certbot (pas dépendre uniquement Cloudflare)
- [ ] **DNS** — configurer A records + CNAME

### 3.2 Hébergement cloud

- [ ] **Choisir l'hébergeur** (recommandé pour démarrer) :
  - **Hetzner CX22** (4€/mois, 2 vCPU, 4GB RAM, Berlin EU) = suffisant pour 10–20 mosquées
  - Ou **Contabo VPS S** (5€/mois, Frankfurt)
  - PostgreSQL managé : **Supabase free** (démarrer) → Render PostgreSQL $7/mois (croissance)
- [ ] **Déploiement cloud** — adapter `docker-compose.yml` pour prod cloud (env variables, volumes persistants)
- [ ] **Migration données dev Pi → cloud** — `pg_dump` Pi → `pg_restore` cloud, valider

### 3.3 CI/CD

- [ ] **GitHub Actions pipeline** :
  - [ ] Sur chaque push `main` : `pytest` complet → si vert, build image Docker
  - [ ] Sur tag `v*` : build + push Docker Hub/GHCR + déploiement auto cloud
  - [ ] Notification Slack/email si build échoue
- [ ] **Script de déploiement** `scripts/deploy.sh` :
  ```bash
  git pull && docker compose build backend-prod && docker compose up -d && python manage.py migrate
  ```
- [ ] **Zero-downtime deploy** — `gunicorn --preload` + health check Nginx (`/api/health/`)
- [ ] **Endpoint de santé** `GET /api/health/` → `{"status": "ok", "db": "ok", "version": "x.y.z"}`

### 3.4 Backups cloud

- [ ] **Backup vers S3/Backblaze B2** (< 1€/mois pour commencer) — configurer `AWS_*` variables
- [ ] **Retention policy** — 7 jours quotidien + 4 semaines hebdo + 3 mois mensuel
- [ ] **Test de restauration documenté** — procédure écrite + testé une fois sur instance fraîche
- [ ] **Alertes backup** — notification si le backup échoue (email ou webhook Discord)

### 3.5 Monitoring

- [ ] **Uptime monitoring** — UptimeRobot (gratuit) sur `https://app.mosqueemanager.fr/api/health/`
- [ ] **Alertes downtime** — email/SMS si > 2 min d'indisponibilité
- [ ] **Logs centralisés** — `docker logs` suffisant pour démarrer, documenter la commande
- [ ] **Sentry (optionnel mais recommandé)** — capturer les erreurs 500 en production avec contexte

---

## P4 — Onboarding automatisé 🟠

> Aujourd'hui : création manuelle via `manage.py shell`. Pour un SaaS, ça doit être automatique.

### 4.1 Signup self-service (si SaaS public)

- [ ] **Page d'inscription** `signup.html` — formulaire : nom mosquée, email admin, mot de passe, nom, ville
- [ ] **API `POST /api/onboarding/register/`** — crée : tenant + mosquée + MosqueSettings + SchoolYear + MembershipYear + user ADMIN
- [ ] **Email de confirmation** — lien de validation email avant activation
- [ ] **Trial automatique** — 30 jours gratuits à la création (via `trial_ends_at` sur le tenant)
- [ ] **`manage.py expire_trials`** — déjà en place ✅, vérifier qu'il désactive bien l'accès

### 4.2 Onboarding guidé (premier login)

- [ ] **Wizard first-run** — si `MosqueSettings` non configuré → redirect vers page onboarding 5 étapes :
  1. Nom mosquée + ville
  2. Année scolaire active + niveaux
  3. Tarifs école + cotisation
  4. Créer premier utilisateur non-ADMIN
  5. ✅ Prêt → redirect dashboard
- [ ] **Données de démo** — bouton "Charger des données d'exemple" pour tester sans import réel
- [ ] **Guide d'import** — tooltip/aide contextuelle sur la page d'import Excel (format attendu, exemple)

### 4.3 Déploiement nouvelle mosquée (actuel = manuel)

- [ ] **Script automatisé** `scripts/deploy-new-mosque.sh` (déjà mentionné dans `DEPLOY-NEW-MOSQUE.md`) :
  - Crée le tenant PostgreSQL
  - Lance les migrations
  - Crée le superuser mosquée
  - Envoie email de bienvenue
- [ ] **DEPLOY-NEW-MOSQUE.md** — valider que la doc est à jour et testée

---

## P5 — Monétisation & billing 🟠

### 5.1 Modèle de prix (recommandation)

| Plan | Prix | Limite | Cible |
|------|------|--------|-------|
| **Gratuit / Trial** | 0€ | 30 jours, toutes features | Découverte |
| **Essentiel** | 9€/mois | 1 mosquée, sans limite d'utilisateurs | Petite association |
| **Pro** | 19€/mois | 1 mosquée + support prioritaire + export avancé | Mosquée active |
| *(futur)* **Multi-sites** | 49€/mois | 5 mosquées | Fédération |

> 💡 **Conseil** : commencer avec Essentiel à 9€/mois. C'est psychologiquement accessible pour une asso et couvre largement les coûts serveur.

### 5.2 Intégration paiement

- [ ] **Stripe** (recommandé) ou **Mollie** (plus simple Europe) :
  - [ ] Compte Stripe créé + vérification identité
  - [ ] Webhook `invoice.paid` → activer/prolonger l'abonnement tenant
  - [ ] Webhook `customer.subscription.deleted` → désactiver l'accès (pas supprimer les données)
  - [ ] Page de paiement `/billing/` — choisir plan, entrer CB, confirmer
- [ ] **Modèle `Subscription`** :
  ```python
  Subscription(tenant, plan, status, stripe_subscription_id, current_period_end, trial_ends_at)
  ```
- [ ] **Middleware `check_subscription`** — si `status != active` et trial expiré → redirect vers `/billing/`
- [ ] **Factures** — Stripe génère les factures PDF automatiquement ✅

### 5.3 Gestion des fins de trial / impayés

- [ ] **Email J-7 avant fin trial** — "Votre essai gratuit se termine dans 7 jours"
- [ ] **Email J-0** — "Votre essai a expiré — choisir un abonnement pour continuer"
- [ ] **Grace period 7 jours après impayé** — avant blocage complet (pour CB expirée, etc.)
- [ ] **Données conservées 30 jours après désabonnement** — puis suppression automatique avec email d'avertissement J-7

---

## P6 — UX/UI polish 🟡

### 6.1 Responsive mobile

- [ ] **Audit mobile** — ouvrir l'app sur iPhone/Android, identifier les écrans cassés
- [ ] **Tableaux sur mobile** — scroll horizontal ou vue "cartes" pour les tableaux denses
- [ ] **Modal sur mobile** — vérifier que les modals ne dépassent pas l'écran

### 6.2 États vides & erreurs

- [ ] **Empty states** — quand il n'y a pas encore de données : message + bouton d'action (ex: "Aucune famille — Ajouter la première famille →")
- [ ] **Loader** — spinner visible pendant les appels API (déjà dans `ui.js` ?)
- [ ] **Toast notifications** — feedback utilisateur après chaque action (sauvegarde ✅, erreur ❌, suppression 🗑️)
- [ ] **Page 404** — si URL inconnue
- [ ] **Session expirée** — message clair "Votre session a expiré" + redirect login (pas juste un écran blanc)

### 6.3 Performance

- [ ] **Pagination** sur les listes longues (familles, membres, transactions) — déjà sur l'API ? Vérifier le frontend
- [ ] **Recherche temps réel** — debounce 300ms sur les champs de recherche
- [ ] **Chargement initial** — éviter de tout charger au login (lazy loading par section)

### 6.4 Accessibilité minimale

- [ ] **Contraste couleurs** — vérifier ratio WCAG AA sur boutons et textes
- [ ] **Labels `for`** sur tous les `<input>` dans les formulaires
- [ ] **Focus visible** sur les éléments interactifs (pas de `outline: none` global)

---

## P7 — Légal & documentation 🟡

### 7.1 Documents légaux

- [ ] **CGU (Conditions Générales d'Utilisation)** — en français, simples, 1 page :
  - Objet du service
  - Responsabilités (hébergement, données)
  - Tarifs et résiliation
  - Données personnelles
- [ ] **Politique de confidentialité (RGPD)** — données collectées, durée, droits, contact DPO
- [ ] **Mentions légales** — éditeur, hébergeur, contact
- [ ] **CGV (Conditions Générales de Vente)** — si SaaS payant : tarifs, remboursement, résiliation
- [ ] **Page légale** `/legal/` ou footer avec liens

### 7.2 Documentation utilisateur

- [ ] **Guide de démarrage rapide** (1 page PDF ou web) :
  - Se connecter
  - Ajouter une famille / un enfant
  - Enregistrer un paiement
  - Générer un reçu PDF
  - Exporter les données
- [ ] **FAQ** — 10 questions fréquentes (mot de passe oublié, import Excel, reçu PDF, etc.)
- [ ] **Vidéo de démo** (optionnel mais très efficace) — 3 min screencast Loom

### 7.3 Documentation technique

- [ ] **`INSTALL.md`** — valider qu'il est à jour (Raspberry Pi + cloud)
- [ ] **`DEPLOY-NEW-MOSQUE.md`** — valider + tester end-to-end
- [ ] **`.env.example`** — vérifier que toutes les variables sont documentées avec exemples
- [ ] **`WORKFLOW-DEV.md`** — règles git, review, déploiement

---

## P8 — Support client & monitoring 🟢

### 8.1 Canal de support

- [ ] **Email de support** `support@mosqueemanager.fr` (ou alias Gmail pour commencer)
- [ ] **Délai de réponse affiché** — "Réponse sous 24–48h" (être réaliste)
- [ ] **Formulaire de contact** dans l'app — bouton "?" ou "Aide" dans le nav → mailto ou form

### 8.2 Communication

- [ ] **Landing page** `mosqueemanager.fr` (simple, 1 page) :
  - Logo + accroche
  - 3 fonctionnalités clés avec screenshots
  - Tarifs
  - CTA "Essayer gratuitement 30 jours"
  - Contact
- [ ] **Email marketing** — Brevo (ex-Sendinblue, gratuit jusqu'à 300/j) pour :
  - Email de bienvenue
  - Email fin trial
  - Newsletter mensuelle (optionnel)

### 8.3 Monitoring applicatif

- [ ] **Logs structurés** — format JSON pour faciliter la lecture en prod
- [ ] **`/api/health/`** endpoint — statut DB, statut cache, version app
- [ ] **Alertes** — UptimeRobot + email si down
- [ ] **Dashboard admin SaaS** (interne, pour toi) — voir le nombre de tenants actifs, trials en cours, derniers signups

---

## Checklist de lancement (Go/No-Go)

Avant d'accepter le premier client payant, cocher TOUS ces points :

### ✅ Technique
- [ ] 0 bug critique connu
- [ ] Tous les tests passent en CI (GitHub Actions)
- [ ] HTTPS fonctionnel (certificat valide)
- [ ] Backup quotidien configuré + 1 restore testé
- [ ] `Restarting` containers = 0 en production
- [ ] Rate limiting sur `/api/auth/login/`
- [ ] Monitoring uptime actif

### ✅ Produit
- [ ] Onboarding complet testé de A à Z (signup → premier paiement enregistré → reçu PDF)
- [ ] Import Excel testé avec fichier réel
- [ ] Export CSV testé
- [ ] Reçus PDF école + cotisations testés
- [ ] KPI screen affiché sur TV/tablette
- [ ] Session expirée gérée proprement

### ✅ Business
- [ ] CGU + Politique de confidentialité en ligne
- [ ] Stripe configuré + 1 paiement test effectué
- [ ] Email de support créé + testé
- [ ] Landing page en ligne
- [ ] Domaine + SSL opérationnel

---

## Ordre de priorité recommandé (sprint planning)

```
Semaine 1 (CRITIQUE — ne pas lancer sans ça)
  ├── Fix Cloudflare Tunnel (Restarting 255)
  ├── Test UI complet gestion utilisateurs
  ├── Test UI reçus PDF (école + cotisations)
  ├── Fix import Excel (test fichier réel)
  └── Endpoint /api/health/

Semaine 2 (SÉCURITÉ)
  ├── Rate limiting login
  ├── Headers sécurité Nginx
  ├── Audit isolation multi-tenant (2 tenants test)
  └── Messages d'erreur API propres

Semaine 3 (INFRA)
  ├── Choix hébergeur + déploiement cloud
  ├── Domaine + SSL
  ├── GitHub Actions CI (tests auto)
  └── Backup vers S3/B2 + alerte si échec

Semaine 4 (ONBOARDING)
  ├── Page signup self-service
  ├── API register (créer tenant auto)
  ├── Wizard first-run
  └── Email de bienvenue

Semaine 5 (BILLING)
  ├── Stripe intégration
  ├── Modèle Subscription
  ├── Middleware check_subscription
  └── Emails trial (J-7, J-0)

Semaine 6 (POLISH + LÉGAL)
  ├── Responsive mobile audit + fixes
  ├── Empty states + toasts
  ├── CGU + Politique de confidentialité
  ├── Landing page
  └── Documentation utilisateur

Semaine 7 (LANCEMENT 🚀)
  ├── Checklist Go/No-Go complète
  ├── Test end-to-end avec première vraie mosquée
  ├── Monitoring uptime actif
  └── ✅ Ouvrir les inscriptions
```

---

## Ce qui est explicitement hors scope V1

> Ces fonctionnalités seront dans V2+ après les premiers clients et revenus récurrents.

- Application mobile (iOS/Android)
- App adhérents/familles (portail self-service)
- Paiement en ligne pour les familles (HelloAsso/Stripe Checkout)
- Notifications SMS
- Import automatique relevé bancaire (OCR)
- Rapport comptable annuel PDF complet (compte de résultat)
- Multi-mosquées sur un seul abonnement (fédération)
- API publique (webhooks, intégrations tierces)
- IA / suggestions automatiques

---

*Version 1.0 — roadmap de lancement*  
*Auteur : Badreddine*
