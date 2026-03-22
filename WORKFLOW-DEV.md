# 🔄 Workflow Dev → Production

> Memo : je modifie du code sur mon Mac, je push sur GitHub,
> je mets à jour le(s) Raspberry Pi.
>
> Pour déployer une **nouvelle mosquée** → voir `DEPLOY-NEW-MOSQUE.md`

---

## Principe fondamental : Code ≠ Données ≠ Config

```
┌─────────────────────────────────────────────────────────┐
│  GIT (code — identique partout)                         │
│  backend/ frontend/ nginx/ docker-compose.yml deploy.sh │
├─────────────────────────────────────────────────────────┤
│  .env (config — UNIQUE par instance, jamais dans git)   │
│  DJANGO_SECRET_KEY, POSTGRES_PASSWORD, ALLOWED_HOSTS…   │
├─────────────────────────────────────────────────────────┤
│  Volume Docker postgres_data (données — JAMAIS effacé)  │
│  Familles, enfants, paiements, adhérents, paramètres…   │
└─────────────────────────────────────────────────────────┘
```

**Un `git pull` + rebuild ne touche JAMAIS ni la DB ni le `.env`.**

---

## Cas 1 — Modification frontend uniquement (HTML/CSS/JS)

> `frontend/index.html`, `frontend/css/*.css`, `frontend/js/*.js`

```bash
# Sur le Mac — commit et push
git add .
git commit -m "feat/fix: description"
git push origin main
```

```bash
# Sur le Pi (SSH)
cd ~/MManager && git pull origin main
docker compose --profile prod restart nginx
```

✅ **Pas de rebuild** — nginx monte `frontend/` en volume, un restart suffit.

---

## Cas 2 — Modification backend Python (views, serializers...)

> `backend/config/`, `backend/core/`, `backend/school/`, etc.  
> **Sans nouveau modèle ni champ** (pas de migration)

```bash
# Sur le Mac — commit et push
git add . && git commit -m "feat/fix: description" && git push origin main
```

```bash
# Sur le Pi (SSH)
cd ~/MManager && git pull origin main
docker compose --profile prod build backend-prod
docker compose --profile prod up -d --no-deps backend-prod
```

> `--no-deps` = ne redémarre pas db, nginx, cloudflared.

---

## Cas 3 — Nouvelle migration Django ⚠️ (nouveau model, nouveau champ)

### Règle d'or : générer la migration sur le Mac, la committer, la déployer

```bash
# 1. Sur le Mac — générer la migration LOCALEMENT
docker compose exec backend python manage.py makemigrations --name="description_courte"

# 2. Vérifier ce qui a été généré
git diff backend/*/migrations/

# 3. Committer ET la migration ET le model
git add backend/ && git commit -m "feat: description (+ migration)" && git push origin main
```

```bash
# 4. Sur le Pi — déployer
cd ~/MManager && git pull origin main
docker compose --profile prod build backend-prod
docker compose --profile prod up -d --no-deps backend-prod
sleep 5
docker compose --profile prod exec -T backend-prod python manage.py migrate
```

### ⚠️ Pourquoi NE PAS générer les migrations sur le Pi

Si on génère sur le Pi ET sur le Mac, on obtient deux fichiers `0005_xxx.py`
avec le même numéro mais des noms différents → conflit au déploiement suivant.  
**Toujours générer sur le Mac, jamais sur le Pi.**

### Vérifier l'état des migrations

```bash
# Quelles migrations sont appliquées ?
docker compose --profile prod exec backend-prod python manage.py showmigrations

# Y a-t-il des migrations en attente ?
docker compose --profile prod exec backend-prod python manage.py migrate --check
```

---

## Cas 4 — Modification nginx.conf

```bash
git add nginx/ && git commit -m "fix(nginx): description" && git push origin main
```

```bash
cd ~/MManager && git pull origin main
docker compose --profile prod restart nginx
```

✅ Pas de rebuild — nginx.conf est monté en volume.

---

## Cas 5 — Nouveau package Python (requirements.txt)

```bash
git add requirements.txt && git commit -m "chore: ajout package xxx" && git push origin main
```

```bash
cd ~/MManager && git pull origin main
docker compose --profile prod build backend-prod
docker compose --profile prod up -d --no-deps backend-prod
```

---

## Cas 6 — Tout mettre à jour (safe, 5 min)

```bash
cd ~/MManager && ./deploy.sh
```

> rebuild tout, relance tout, applique les migrations. Garanti sans surprise.

---

## 🗂️ Tableau récapitulatif

| Fichier modifié | Rebuild image ? | migrate ? | Commande rapide |
|---|:---:|:---:|---|
| `frontend/` (HTML/CSS/JS) | ❌ | ❌ | `git pull && restart nginx` |
| `nginx/nginx.conf` | ❌ | ❌ | `git pull && restart nginx` |
| `backend/*.py` (sans migration) | ✅ | ❌ | `git pull && build && up -d --no-deps backend-prod` |
| `backend/*.py` (avec migration) | ✅ | ✅ | idem + `manage.py migrate` |
| `requirements.txt` | ✅ | ❌ | idem sans migrate |
| Tout à la fois | ✅ | ✅ | `./deploy.sh` |

---

## 🕌 Multi-mosquées — mettre à jour toutes les instances

```bash
# Depuis le Mac — liste des instances dans scripts/instances.conf
chmod +x scripts/update_all.sh
./scripts/update_all.sh
```

Le script se connecte à chaque Pi en SSH et applique :
`git pull` → `build` → `up -d` → `migrate`

**Ajouter une nouvelle mosquée à la liste :**

```bash
echo "mosquee@192.168.X.XX NomMosquée" >> scripts/instances.conf
git add scripts/instances.conf && git commit -m "chore: add NomMosquée instance"
```

---

## 🔑 Paramètres spécifiques par mosquée

Deux niveaux de config, bien séparés :

### Niveau 1 — `.env` (infra/secrets, jamais dans git)

| Variable | Ce que c'est |
|---|---|
| `DJANGO_SECRET_KEY` | Clé de signature JWT — unique par instance |
| `POSTGRES_PASSWORD` | Mot de passe DB — unique par instance |
| `ALLOWED_HOSTS` | IP locale + domaine ngrok — unique par instance |
| `NGROK_AUTHTOKEN` | Token ngrok — unique par compte |
| `BACKUP_PASSPHRASE` | Passphrase chiffrement backups — unique par instance |

### Niveau 2 — `MosqueSettings` (DB, modifiable depuis l'UI)

| Champ | Ce que c'est |
|---|---|
| `mosque_name`, `mosque_timezone` | Identité |
| `school_fee_default`, `school_fee_mode` | Tarifs école |
| `school_levels` | Niveaux scolaires |
| `membership_fee_amount`, `membership_fee_mode` | Cotisation |
| `smtp_host/port/user/password` | Config email |
| `receipt_logo_url`, `receipt_address` | Reçus PDF |
| `active_school_year_label` | Année scolaire active |

> Ces paramètres **survivent aux mises à jour** — ils sont en DB, pas dans le code.

---

## 💡 Alias SSH utiles (à mettre dans `~/.zshrc`)

```bash
# Connexion rapide
alias sshpi="ssh mosquee@192.168.0.14"

# Mise à jour rapide frontend
alias pi-front="ssh mosquee@192.168.0.14 'cd ~/MManager && git pull && docker compose --profile prod restart nginx'"

# Mise à jour complète
alias pi-deploy="ssh mosquee@192.168.0.14 'cd ~/MManager && ./deploy.sh'"

# Voir les logs live
alias pi-logs="ssh mosquee@192.168.0.14 'cd ~/MManager && docker compose --profile prod logs -f'"

# État des containers
alias pi-status="ssh mosquee@192.168.0.14 'docker compose --profile prod ps'"
```

```bash
source ~/.zshrc  # recharger
```


---

## Cas 1 — Modification frontend uniquement (HTML/CSS/JS)

> `frontend/index.html`, `frontend/style.css`, etc.

```bash
# Sur le Mac — commit et push
git add .
git commit -m "feat/fix: description"
git push origin main
```

```bash
# Sur le Pi (SSH)
cd ~/MManager
git pull origin main
docker compose --profile prod restart nginx
```

✅ **Pas de rebuild** — nginx monte le dossier `frontend/` en volume, un restart suffit.

---

## Cas 2 — Modification backend Python (views, models, serializers...)

> `backend/config/`, `backend/core/`, `backend/school/`, etc.

```bash
# Sur le Mac — commit et push
git add .
git commit -m "feat/fix: description"
git push origin main
```

```bash
# Sur le Pi (SSH)
cd ~/MManager
git pull origin main
docker compose --profile prod build backend-prod
docker compose --profile prod up -d --no-deps backend-prod
```

> `--no-deps` = ne redémarre pas les autres services (db, nginx...)

---

## Cas 3 — Nouvelle migration Django (nouveau model, champ modifié...)

```bash
# Sur le Mac — commit et push
git add .
git commit -m "feat: description"
git push origin main
```

```bash
# Sur le Pi (SSH)
cd ~/MManager
git pull origin main
docker compose --profile prod build backend-prod
docker compose --profile prod up -d --no-deps backend-prod
sleep 10
docker compose --profile prod exec backend-prod python manage.py migrate
```

---

## Cas 4 — Modification nginx.conf

> `nginx/nginx.conf`

```bash
# Sur le Mac — commit et push
git add .
git commit -m "fix(nginx): description"
git push origin main
```

```bash
# Sur le Pi (SSH)
cd ~/MManager
git pull origin main
docker compose --profile prod restart nginx
```

✅ **Pas de rebuild** — nginx.conf est monté en volume.

---

## Cas 5 — Modification requirements.txt (nouveau package Python)

```bash
# Sur le Mac — commit et push
git add .
git commit -m "chore: ajout package xxx"
git push origin main
```

```bash
# Sur le Pi (SSH)
cd ~/MManager
git pull origin main
docker compose --profile prod build backend-prod
docker compose --profile prod up -d --no-deps backend-prod
```

---

## Cas 6 — Tout mettre à jour d'un coup (safe)

```bash
# Sur le Pi (SSH) — met tout à jour proprement
cd ~/MManager
git pull origin main
./deploy.sh
```

> `deploy.sh` rebuild tout, relance tout, applique les migrations.
> Plus lent (~5 min) mais garanti sans surprise.

---

## 🔑 Tableau récapitulatif

| Fichier modifié | Rebuild ? | Commande Pi |
|---|---|---|
| `frontend/*.html/css/js` | ❌ | `git pull && docker compose --profile prod restart nginx` |
| `nginx/nginx.conf` | ❌ | `git pull && docker compose --profile prod restart nginx` |
| `backend/*.py` (sans migration) | ✅ | `git pull && docker compose ... build && up -d --no-deps backend-prod` |
| `backend/*.py` (avec migration) | ✅ | idem + `manage.py migrate` |
| `requirements.txt` | ✅ | idem que backend |
| Tout à la fois | ✅ | `git pull && ./deploy.sh` |

---

## 💡 Astuce — Alias SSH utile

Ajoute ça sur ton Mac dans `~/.zshrc` pour ne pas retaper l'IP :

```bash
alias sshpi="ssh mosquee@192.168.0.14"
alias piupdate="ssh mosquee@192.168.0.14 'cd ~/MManager && git pull origin main && docker compose --profile prod restart nginx'"
```

Rechargement :
```bash
source ~/.zshrc
```

Ensuite tu peux juste taper `sshpi` pour te connecter ou `piupdate` pour un update rapide frontend.
