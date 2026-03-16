# 🕌 Guide — Déployer une nouvelle mosquée

## Vue d'ensemble

Chaque mosquée tourne sur son propre serveur (Raspberry Pi ou VPS Linux).  
Le code vient du **même dépôt git**. Seuls `.env` et la base de données sont spécifiques à chaque instance.

```
                       ┌────────────────────────────┐
  GitHub               │  github.com/BadreddineEK/  │
  (code source)        │  MManager  ← source unique │
                       └────────────┬───────────────┘
                                    │ git pull
                 ┌──────────────────┼──────────────────┐
                 ▼                  ▼                   ▼
        ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
        │ Pi Meximieux   │ │ Pi Lyon        │ │ VPS Paris      │
        │ .env propre    │ │ .env propre    │ │ .env propre    │
        │ DB locale      │ │ DB locale      │ │ DB locale      │
        └────────────────┘ └────────────────┘ └────────────────┘
```

---

## Prérequis serveur

- Raspberry Pi 4/5 ou PC Linux / VPS Ubuntu 22.04+
- Accès internet
- RAM : 1 Go minimum (2 Go recommandé)
- Stockage : 8 Go minimum (16 Go recommandé)
- SSH activé

---

## Étapes (environ 15 minutes)

### 1. Cloner le dépôt

```bash
cd ~
git clone https://github.com/BadreddineEK/MManager.git
cd MManager
```

### 2. Créer le `.env` spécifique à cette mosquée

```bash
cp .env.example .env
nano .env  # ou: vim .env
```

**Valeurs obligatoires à changer :**

| Variable | Valeur à mettre | Comment générer |
|----------|-----------------|-----------------|
| `DJANGO_SECRET_KEY` | Chaîne aléatoire longue | `python3 -c "import secrets; print(secrets.token_urlsafe(60))"` |
| `POSTGRES_PASSWORD` | Mot de passe fort | `python3 -c "import secrets; print(secrets.token_urlsafe(20))"` |
| `DATABASE_URL` | Doit contenir le même password | Voir modèle dans `.env.example` |
| `ALLOWED_HOSTS` | IP locale du Pi + domaine ngrok | `hostname -I \| awk '{print $1}'` |
| `CSRF_TRUSTED_ORIGINS` | Idem | — |
| `BACKUP_PASSPHRASE` | Passphrase pour chiffrement backups | Chaîne aléatoire |

**Variables optionnelles :**

| Variable | Usage |
|----------|-------|
| `NGROK_AUTHTOKEN` | Accès depuis l'extérieur (compte ngrok.com gratuit) |
| `NGROK_DOMAIN` | Domaine statique ngrok |
| `CLOUDFLARE_TUNNEL_TOKEN` | Alternative à ngrok (si domaine existant) |
| `TIMEZONE` | Fuseau horaire (défaut : `Europe/Paris`) |

### 3. Lancer le déploiement

```bash
chmod +x deploy.sh
./deploy.sh
```

Le script fait automatiquement :
- Installation de Docker si absent
- Build des images
- Démarrage de la DB + backend + nginx
- Migrations Django
- Configuration ngrok (si token renseigné)

### 4. Créer le superutilisateur

```bash
docker compose --profile prod exec backend-prod \
    python manage.py createsuperuser
```

Saisir : email, username, mot de passe.

### 5. Configurer la mosquée (première connexion)

1. Ouvrir `http://IP_DU_PI` dans le navigateur
2. Se connecter avec le superutilisateur
3. Aller dans **⚙️ Paramètres**
4. Renseigner : nom mosquée, fuseau horaire, année scolaire, niveaux, tarifs
5. Cliquer **💾 Enregistrer**

### 6. (Optionnel) Ajouter cette instance dans `scripts/instances.conf`

```bash
# Sur votre machine de développement, dans le repo :
echo "mosquee@192.168.X.XX NomMosquée" >> scripts/instances.conf
git add scripts/instances.conf
git commit -m "chore: add NomMosquée to instances"
git push
```

---

## Comprendre la séparation Code / Données / Config

```
┌─────────────────────────────────────────────────────────┐
│  Ce qui vient de git (identique sur toutes les instances)│
│  ├── backend/   → code Django (views, models, migrations)│
│  ├── frontend/  → HTML/CSS/JS                           │
│  ├── docker-compose.yml                                  │
│  └── deploy.sh                                          │
├─────────────────────────────────────────────────────────┤
│  Ce qui est PROPRE à chaque instance (jamais dans git)   │
│  ├── .env              → secrets + URLs spécifiques      │
│  └── Volume Docker     → base de données PostgreSQL      │
│       └── core_mosquesettings → config métier mosquée   │
│            (nom, tarifs, niveaux, SMTP, logo…)          │
└─────────────────────────────────────────────────────────┘
```

### Ce qui SE PASSE lors d'un `git pull` + redémarrage

✅ **Préservé :**
- Toutes les données (familles, enfants, paiements, adhérents…)
- La configuration mosquée (MosqueSettings)
- Les utilisateurs et leurs mots de passe
- Le fichier `.env`

🔄 **Mis à jour :**
- Le code de l'application (nouvelles fonctionnalités, corrections)
- Les migrations Django (nouvelles colonnes ajoutées automatiquement)
- Le frontend (HTML/CSS/JS)

❌ **Jamais touché :**
- Le volume Docker `postgres_data`
- Le fichier `.env`

---

## Mettre à jour une seule mosquée

```bash
ssh mosquee@IP_DU_PI
cd ~/MManager
./deploy.sh
```

Ou sans le script complet (mise à jour rapide) :

```bash
ssh mosquee@IP_DU_PI "cd ~/MManager && \
    git pull && \
    docker compose --profile prod build backend-prod --quiet && \
    docker compose --profile prod up -d --no-deps backend-prod && \
    sleep 3 && \
    docker compose --profile prod exec -T backend-prod python manage.py migrate --noinput"
```

## Mettre à jour TOUTES les mosquées d'un coup

```bash
# Depuis votre machine de développement
chmod +x scripts/update_all.sh
./scripts/update_all.sh
```

---

## Sauvegardes

### Backup manuel

```bash
docker compose --profile prod run --rm backup
```

Le fichier chiffré est déposé dans `~/MManager/backups/`.

### Vérifier les backups automatiques

```bash
# Les backups tournent quotidiennement via le container 'backup'
docker compose --profile prod logs backup | tail -20
ls -lh ~/MManager/backups/
```

### Restaurer une sauvegarde

```bash
# 1. Déchiffrer (passphrase dans .env → BACKUP_PASSPHRASE)
openssl enc -aes-256-cbc -d -in backups/mosque_backup_YYYYMMDD.sql.gz.enc \
    -out restore.sql.gz -pass env:BACKUP_PASSPHRASE

# 2. Décompresser
gunzip restore.sql.gz

# 3. Restaurer (arrêter le backend d'abord)
docker compose --profile prod stop backend-prod
docker compose --profile prod exec -T db \
    psql -U mosque_user -d mosque_db < restore.sql
docker compose --profile prod start backend-prod
```

---

## Commandes utiles au quotidien

```bash
# Logs en temps réel
docker compose --profile prod logs -f

# Logs d'un seul service
docker compose --profile prod logs -f backend-prod

# Statut des containers
docker compose --profile prod ps

# Redémarrer le backend uniquement
docker compose --profile prod restart backend-prod

# Console Django (debugging)
docker compose --profile prod exec backend-prod python manage.py shell

# Lister les migrations appliquées
docker compose --profile prod exec backend-prod python manage.py showmigrations

# Vérification configuration Django
docker compose --profile prod exec backend-prod python manage.py check --deploy
```

---

## FAQ

**Q : Les données d'une mosquée sont-elles accessibles depuis une autre ?**  
R : Non. Chaque instance a sa propre base de données sur son propre serveur. L'isolation est physique.

**Q : Peut-on partager un serveur entre deux mosquées ?**  
R : Oui, via le modèle multi-tenant (table `mosque_id` sur toutes les tables). Contacter le développeur pour configurer ce mode.

**Q : Que se passe-t-il si le Pi est éteint ?**  
R : L'app est inaccessible de l'extérieur. Les données sont intactes. Au redémarrage, Docker relance tout automatiquement (`restart: unless-stopped`).

**Q : Comment migrer vers le cloud (Render, VPS) ?**  
R : 
1. `pg_dump` sur le Pi → import vers la DB cloud
2. Mettre à jour `DATABASE_URL` dans `.env` sur le cloud
3. Le code ne change pas

**Q : Peut-on tester une mise à jour avant de la déployer ?**  
R : Oui — tester en local d'abord (`docker compose up` sans `--profile prod`), puis déployer.
