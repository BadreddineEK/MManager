# 🔄 Workflow Dev → Production

> Memo : je modifie du code sur mon Mac, je push sur GitHub,
> je mets à jour le Raspberry Pi.

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
alias sshpi="ssh mosquee@192.168.0.13"
alias piupdate="ssh mosquee@192.168.0.13 'cd ~/MManager && git pull origin main && docker compose --profile prod restart nginx'"
```

Rechargement :
```bash
source ~/.zshrc
```

Ensuite tu peux juste taper `sshpi` pour te connecter ou `piupdate` pour un update rapide frontend.
