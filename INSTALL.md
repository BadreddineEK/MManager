# 📦 Guide d'installation — Mosquée Manager
## Raspberry Pi 4/5 + Cloudflare Tunnel

> **Scénario** : Le Raspberry Pi est branché dans la mosquée (WiFi + câble réseau).
> L'app est accessible depuis le réseau local ET depuis n'importe où via Cloudflare.

---

## 🛒 Matériel nécessaire

| Composant | Modèle recommandé | Prix indicatif |
|---|---|---|
| Raspberry Pi | Pi 4 (4GB) ou Pi 5 | 70-90 € |
| Carte SD | 32GB minimum (SanDisk Endurance) | 10-15 € |
| Alimentation | Officielle Raspberry Pi | 10 € |
| Câble réseau | RJ45 Cat5e | 3 € |
| Boîtier | N'importe lequel | 10 € |

> 💡 Un vieux PC Linux/Windows avec WSL2 fonctionne aussi très bien.

---

## 📋 Vue d'ensemble des étapes

```
1. Préparer le Raspberry Pi (OS + SSH)
2. Cloner le projet
3. Configurer .env
4. Lancer l'app (./deploy.sh)
5. Configurer le tunnel Cloudflare
6. Tester l'accès distant
```

---

## Étape 1 — Préparer le Raspberry Pi

### 1.1 Installer Raspberry Pi OS
1. Télécharger **Raspberry Pi Imager** : https://www.raspberrypi.com/software/
2. Choisir : **Raspberry Pi OS Lite (64-bit)** — sans interface graphique, plus léger
3. Dans les paramètres avancés de l'Imager (icône ⚙️) :
   - ✅ Activer SSH
   - ✅ Définir un nom d'utilisateur (ex: `mosque`) et un mot de passe fort
   - ✅ Configurer le WiFi de la mosquée (SSID + mot de passe)
   - ✅ Définir le hostname : `mosque-manager`
4. Flasher la carte SD, insérer dans le Pi, brancher et allumer

### 1.2 Se connecter en SSH
```bash
# Depuis ton Mac / PC (même réseau WiFi)
ssh mosque@mosque-manager.local

# Si ça ne fonctionne pas, trouver l'IP du Pi depuis ta box :
# http://192.168.1.1 → liste des appareils connectés
# Puis : ssh mosque@192.168.1.XXX
```

### 1.3 Mettre à jour le système
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl
```

---

## Étape 2 — Cloner le projet

```bash
# Dans le répertoire home
cd ~
git clone https://github.com/BadreddineEK/MManager.git
cd MManager
```

---

## Étape 3 — Configurer le `.env`

```bash
# Copier le template
cp .env.example .env

# Éditer avec nano
nano .env
```

**Valeurs à changer OBLIGATOIREMENT :**

```bash
# 1. Générer une vraie clé secrète Django
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
# → Copier le résultat dans DJANGO_SECRET_KEY=

# 2. Mode production
DJANGO_DEBUG=False

# 3. Mot de passe base de données (au choix)
POSTGRES_PASSWORD=UnMotDePasseFortIci
DATABASE_URL=postgres://mosque_user:UnMotDePasseFortIci@db:5432/mosque_db

# 4. L'URL que Cloudflare va donner (à remplir à l'étape 5)
ALLOWED_HOSTS=localhost,127.0.0.1,TON-TUNNEL.trycloudflare.com
CORS_ALLOWED_ORIGINS=https://TON-TUNNEL.trycloudflare.com
```

Sauvegarder : `Ctrl+O` → `Entrée` → `Ctrl+X`

---

## Étape 4 — Lancer l'application

```bash
# Depuis ~/MManager
chmod +x deploy.sh
./deploy.sh
```

Le script va automatiquement :
- ✅ Installer Docker si absent
- ✅ Builder les images (5-10 min sur Pi 4 — une seule fois)
- ✅ Démarrer tous les services
- ✅ Appliquer les migrations
- ✅ Collecter les fichiers statiques

**À la fin, l'app est accessible sur le réseau local :**
```
http://192.168.1.XXX   (IP du Raspberry Pi)
```

> 💡 Pour trouver l'IP affichée à la fin du script, ou : `hostname -I`

---

## Étape 5 — Configurer le tunnel Cloudflare (accès depuis n'importe où)

### 5.1 Créer un compte Cloudflare (gratuit)
→ https://www.cloudflare.com — s'inscrire gratuitement

### 5.2 Créer le tunnel
1. Aller sur https://one.dash.cloudflare.com
2. **Zero Trust** → **Networks** → **Tunnels** → **Create a tunnel**
3. Choisir : **Cloudflared**
4. Nommer le tunnel : `mosque-manager`
5. Sur la page suivante, copier le **token** (longue chaîne commençant par `eyJ...`)

### 5.3 Ajouter le token dans `.env`
```bash
nano ~/.../MManager/.env
# Coller le token :
CLOUDFLARE_TUNNEL_TOKEN=eyJhIjoixxxxxxxxxxxxxxx...
```

### 5.4 Configurer la destination du tunnel
Dans l'interface Cloudflare, section **"Public Hostname"** :
- **Subdomain** : `mosque` (ou ce que tu veux)
- **Domain** : choisir ton domaine Cloudflare, OU utiliser `trycloudflare.com` (gratuit, sans domaine)
- **Service** : `http://nginx:80`

> 💡 **Sans domaine** : Cloudflare donne une URL gratuite du type `https://mosque-quelquechose.trycloudflare.com`

### 5.5 Mettre à jour `.env` avec l'URL finale
```bash
nano .env
ALLOWED_HOSTS=localhost,127.0.0.1,mosque-quelquechose.trycloudflare.com
CORS_ALLOWED_ORIGINS=https://mosque-quelquechose.trycloudflare.com
```

### 5.6 Relancer le déploiement
```bash
./deploy.sh
```

---

## Étape 6 — Vérifier que tout fonctionne

```bash
# Statut des services
docker compose --profile prod ps

# Health check
curl http://localhost/health/

# Logs en temps réel
docker compose --profile prod logs -f
```

**Test depuis ton téléphone (même WiFi mosquée) :**
→ Ouvrir `http://192.168.1.XXX` dans le navigateur

**Test depuis chez toi :**
→ Ouvrir `https://mosque-quelquechose.trycloudflare.com`

---

## 🔄 Mettre à jour l'application

À chaque nouvelle version, depuis le Raspberry Pi :
```bash
cd ~/MManager
./deploy.sh
```
C'est tout — le script fait tout automatiquement.

---

## 🛠️ Commandes utiles au quotidien

```bash
# Voir les logs en direct
docker compose --profile prod logs -f

# Voir les logs d'un service spécifique
docker compose --profile prod logs -f backend-prod
docker compose --profile prod logs -f nginx

# Redémarrer un service
docker compose --profile prod restart backend-prod

# Faire un backup manuel
docker compose --profile prod run --rm backup

# Arrêter toute l'application
docker compose --profile prod down

# Démarrer après un arrêt
docker compose --profile prod up -d

# Se connecter à la base de données
docker compose --profile prod exec db psql -U mosque_user -d mosque_db
```

---

## 🔒 Sécurité

- ✅ Le port PostgreSQL (5432) **n'est pas exposé** sur le réseau — accès interne Docker uniquement
- ✅ HTTPS géré par Cloudflare (certificat automatique)
- ✅ JWT avec expiration 8h
- ✅ Backups automatiques chaque nuit à 2h
- ⚠️ **Changer le mot de passe admin** après la première connexion : `admin` / `admin1234`

---

## ❓ Dépannage fréquent

| Problème | Solution |
|---|---|
| `./deploy.sh` échoue sur Docker | Fermer et rouvrir la session SSH, relancer |
| L'app ne répond pas sur `localhost` | `docker compose --profile prod logs nginx` |
| Le tunnel Cloudflare ne se connecte pas | Vérifier `CLOUDFLARE_TUNNEL_TOKEN` dans `.env` |
| Erreur de migration | `docker compose --profile prod exec backend-prod python manage.py migrate` |
| Page blanche dans le navigateur | Vider le cache navigateur (Ctrl+Shift+R) |
| Mot de passe oublié | `docker compose --profile prod exec backend-prod python manage.py changepassword admin` |

---

## 📞 Architecture finale

```
┌─────────────────────────────────────────────────────────┐
│                    Raspberry Pi                          │
│                                                         │
│  ┌──────────┐   ┌───────────┐   ┌──────────────────┐   │
│  │ PostgreSQL│   │  Gunicorn  │   │      Nginx       │   │
│  │  (db)    │◄──│ (backend) │◄──│  :80             │   │
│  └──────────┘   └───────────┘   │  /api → backend  │   │
│                                 │  /    → index.html│   │
│  ┌──────────────────────────┐   └────────┬─────────┘   │
│  │   cloudflared (tunnel)   │◄───────────┘             │
│  └──────────────────────────┘                          │
└──────────────────┬──────────────────────────────────────┘
                   │ tunnel chiffré
         ┌─────────▼──────────┐
         │   Cloudflare Edge   │  HTTPS gratuit
         └─────────┬───────────┘
                   │
         ┌─────────▼───────────────┐
         │  Utilisateurs partout   │
         │  https://mosque-xxx.com │
         └─────────────────────────┘
```
