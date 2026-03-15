# � Mosquée Manager — Guide d'installation complet

> **Reproductible** : ce guide fonctionne sur n'importe quel Raspberry Pi 4/5.
> Si tu changes de réseau WiFi ou de Pi, seules quelques variables `.env` changent.
> L'URL d'accès externe (ngrok) reste la même pour toujours.

---

## � Matériel nécessaire

| Composant | Recommandé | Prix indicatif |
|---|---|---|
| Raspberry Pi | Pi 4 (4GB RAM) ou Pi 5 | 70-90 € |
| Carte SD | 32 GB classe 10 (SanDisk Endurance) | 10-15 € |
| Alimentation | Officielle Raspberry Pi USB-C | 10 € |
| Boîtier | N'importe lequel | 5-10 € |

---

## 📋 Vue d'ensemble

```
Étape 1  — Flasher la carte SD (Raspberry Pi Imager)
Étape 2  — Démarrer le Pi et se connecter en SSH
Étape 3  — Mettre à jour le système
Étape 4  — Cloner le projet
Étape 5  — Configurer le .env
Étape 6  — Déployer l'application (./deploy.sh)
Étape 7  — Créer le compte administrateur
Étape 8  — Configurer l'accès externe (ngrok)
Étape 9  — Configurer la mosquée (Django Admin)
Étape 10 — Vérification finale
```

---

## Étape 1 — Flasher la carte SD

1. Télécharger **Raspberry Pi Imager** : https://www.raspberrypi.com/software/
2. Ouvrir Imager :
   - **Choose Device** → Raspberry Pi 4 (ou 5)
   - **Choose OS** → *Raspberry Pi OS (other)* → **Raspberry Pi OS Lite (64-bit)**
   - **Choose Storage** → ta carte SD
3. Cliquer **Next** → **Edit Settings** et remplir :

### Onglet General
| Champ | Valeur |
|---|---|
| Hostname | `mosquee-manager` |
| Username | `mosquee` |
| Password | `Mosquee2026!` *(ou autre — note-le)* |
| Timezone | `Europe/Paris` |
| Keyboard | `fr` |
| **WiFi SSID** | Nom du réseau WiFi |
| **WiFi Password** | Mot de passe WiFi |

### Onglet Services
| Champ | Valeur |
|---|---|
| Enable SSH | ✅ |
| Password authentication | ✅ |

4. **Save** → **Yes** → attendre 5-10 min le flashage

---

## Étape 2 — Démarrer le Pi et se connecter

1. Insérer la carte SD dans le Pi, brancher l'alimentation
2. Attendre **3 minutes** le démarrage complet

### Trouver l'IP du Pi
```bash
# Depuis ton Mac (même réseau WiFi)
ping mosquee-manager.local
# → Note l'IP affichée, ex: 192.168.0.13
```
Si `ping` ne répond pas : regarde les appareils connectés sur ta box (http://192.168.1.1 ou http://192.168.0.1).

### Se connecter en SSH
```bash
ssh mosquee@192.168.0.XX
# Mot de passe : Mosquee2026! (ou celui défini)
```

---

## Étape 3 — Mettre à jour le système

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl
```

---

## Étape 4 — Cloner le projet

```bash
cd ~
git clone https://github.com/BadreddineEK/MManager.git
cd MManager
```

---

## Étape 5 — Configurer le `.env`

```bash
cp .env.example .env
nano .env
```

### Valeurs obligatoires à remplir

**1. Générer une clé secrète Django :**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(60))"
```
→ Copier le résultat dans `DJANGO_SECRET_KEY=`

**2. Générer un mot de passe PostgreSQL :**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(20))"
```
→ Copier dans `POSTGRES_PASSWORD=` ET dans `DATABASE_URL=` (remplacer `CHANGE_MOI`)

**3. Remplir l'IP locale du Pi :**
```bash
hostname -I | awk '{print $1}'
# Ex: 192.168.0.13
```

**4. Résultat final dans `.env` :**
```env
DJANGO_SECRET_KEY=<clé générée>
DJANGO_DEBUG=False
POSTGRES_PASSWORD=<mot de passe généré>
DATABASE_URL=postgres://mosque_user:<mot de passe>@db:5432/mosque_db
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.0.XX,ton-domaine.ngrok-free.app
CSRF_TRUSTED_ORIGINS=http://localhost,http://192.168.0.XX,https://ton-domaine.ngrok-free.app
CORS_ALLOWED_ORIGINS=http://localhost,http://192.168.0.XX,https://ton-domaine.ngrok-free.app
NGROK_AUTHTOKEN=<token ngrok — voir étape 8>
NGROK_DOMAIN=<domaine ngrok — voir étape 8>
HTTPS_ENABLED=true
```

> ⚠️ **Ne jamais commiter le fichier `.env`** — il contient des secrets.

Sauvegarder : `Ctrl+X` → `Y` → `Entrée`

---

## Étape 6 — Déployer l'application

```bash
chmod +x deploy.sh
./deploy.sh
```

Le script fait **tout automatiquement** :
- ✅ Installe Docker si absent
- ✅ Build les images Docker (5-15 min sur Pi 4 — une seule fois)
- ✅ Lance tous les services (nginx, Django, PostgreSQL, backup cron)
- ✅ Applique les migrations de base de données
- ✅ Collecte les fichiers statiques
- ✅ Installe et configure ngrok si `NGROK_AUTHTOKEN` est défini

> 💡 Si Docker vient d'être installé, le script demande de fermer/rouvrir
> la session SSH, puis relancer `./deploy.sh`

**À la fin, l'app est accessible sur le réseau local :**
```
http://192.168.0.XX
http://192.168.0.XX/admin/   ← Django Admin
```

---

## Étape 7 — Créer le compte administrateur

```bash
docker compose --profile prod exec backend-prod python manage.py createsuperuser
```

- **Username** : `admin`
- **Email** : ton email
- **Password** : mot de passe solide (min 8 caractères)

---

## Étape 8 — Configurer l'accès externe (ngrok)

ngrok permet d'accéder à l'app **depuis n'importe où** (domicile, téléphone, déplacement)
sans ouvrir de port sur ta box, sans payer d'hébergeur. **100% gratuit, sans CB.**

### 8.1 Créer un compte ngrok
→ https://ngrok.com — s'inscrire avec Google ou GitHub (gratuit)

### 8.2 Récupérer le token d'authentification
→ https://dashboard.ngrok.com/authtokens → **Copy**

### 8.3 Récupérer ton domaine statique gratuit
→ https://dashboard.ngrok.com/domains
→ Un domaine du type `quelquechose.ngrok-free.app` est attribué automatiquement (permanent)

### 8.4 Mettre à jour le `.env`
```bash
nano ~/MManager/.env
```
Remplir :
```env
NGROK_AUTHTOKEN=<ton token ngrok>
NGROK_DOMAIN=quelquechose.ngrok-free.app
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.0.XX,quelquechose.ngrok-free.app
CSRF_TRUSTED_ORIGINS=http://localhost,http://192.168.0.XX,https://quelquechose.ngrok-free.app
CORS_ALLOWED_ORIGINS=http://localhost,http://192.168.0.XX,https://quelquechose.ngrok-free.app
HTTPS_ENABLED=true
```

### 8.5 Relancer le déploiement
```bash
./deploy.sh
```
Le script installe ngrok et crée automatiquement un service systemd
→ ngrok démarre automatiquement à chaque reboot du Pi.

---

## Étape 9 — Configurer la mosquée (Django Admin)

Ouvrir **http://192.168.0.XX/admin/** → se connecter avec `admin`

### 9.1 Créer la mosquée
**Core → Mosques → Add mosque**
| Champ | Valeur |
|---|---|
| Name | Nom de votre mosquée |
| Slug | généré automatiquement |

### 9.2 Assigner la mosquée à l'admin
**Core → Users → admin**
| Champ | Valeur |
|---|---|
| Mosque | sélectionner la mosquée |
| Role | `admin` |

### 9.3 Créer l'année scolaire
**School → School years → Add school year**
| Champ | Valeur |
|---|---|
| Label | `2025-2026` |
| Mosque | ta mosquée |
| Start date | `2025-09-01` |
| End date | `2026-06-30` |
| Is active | ✅ |

### 9.4 Créer l'année d'adhésion
**Membership → Membership years → Add**
| Champ | Valeur |
|---|---|
| Year | `2026` |
| Mosque | ta mosquée |
| Is active | ✅ |

---

## Étape 10 — Vérification finale

| Test | URL | Résultat attendu |
|---|---|---|
| App en local | `http://192.168.0.XX` | Page de login ✅ |
| App depuis partout | `https://ton-domaine.ngrok-free.app` | Page de login ✅ |
| Admin Django | `http://192.168.0.XX/admin/` | Interface admin ✅ |
| Health check | `curl http://localhost/health/` | `{"status":"ok"}` ✅ |

```bash
# Vérifier l'état de tous les services
docker compose --profile prod ps

# Vérifier ngrok
sudo systemctl status ngrok
```

---

## 🔄 Changer de réseau WiFi

Si tu déplaces le Pi sur un autre réseau WiFi :

### Option A — Via SSH (si accès Ethernet disponible)
```bash
sudo nmtui
# Interface graphique → Activate a connection → choisir le nouveau WiFi
```

### Option B — Via la carte SD (si aucun accès réseau)
1. Éteindre le Pi : `sudo shutdown now`
2. Insérer la carte SD dans ton Mac
3. Dans le volume `bootfs`, créer le fichier `wpa_supplicant.conf` :
```
country=FR
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="NOM_DU_NOUVEAU_WIFI"
    psk="MOT_DE_PASSE_WIFI"
    key_mgmt=WPA-PSK
}
```
4. Réinsérer la carte dans le Pi → redémarrer
5. Trouver la nouvelle IP : `ping mosquee-manager.local`

### Après changement de réseau — Mettre à jour le `.env`
```bash
ssh mosquee@NOUVELLE_IP
cd MManager
nano .env
# Mettre à jour ALLOWED_HOSTS et CSRF_TRUSTED_ORIGINS avec la nouvelle IP
docker compose --profile prod down
docker compose --profile prod build backend-prod
docker compose --profile prod up -d
```

> ✅ **L'URL ngrok ne change pas** — le trésorier garde la même URL externe.

---

## � Commandes utiles au quotidien

```bash
# Se connecter au Pi
ssh mosquee@192.168.0.XX

# Vérifier l'état des services
docker compose --profile prod ps

# Voir les logs en direct
docker compose --profile prod logs -f

# Logs d'un service spécifique
docker compose --profile prod logs -f backend-prod

# Mettre à jour vers la dernière version
./deploy.sh

# Backup manuel
docker compose --profile prod run --rm backup

# Redémarrage complet
docker compose --profile prod down && docker compose --profile prod up -d

# Accès base de données
docker compose --profile prod exec db psql -U mosque_user -d mosque_db

# Vérifier ngrok
sudo systemctl status ngrok
sudo journalctl -u ngrok -n 50
```

---

## 🆘 Résolution des problèmes

| Problème | Solution |
|---|---|
| `./deploy.sh` échoue sur Docker | Ferme/rouvre la session SSH et relance |
| L'app ne répond pas | `docker compose --profile prod logs nginx` |
| Erreur CSRF 403 | Vérifier que l'IP/domaine est dans `CSRF_TRUSTED_ORIGINS` dans `.env`, puis rebuild |
| Cookie `Secure` sur HTTP | Mettre `HTTPS_ENABLED=true` si accès via ngrok, `false` si HTTP local uniquement |
| ngrok ne démarre pas | `sudo journalctl -u ngrok -n 50` — vérifier le token dans `.env` |
| Mot de passe admin oublié | `docker compose --profile prod exec backend-prod python manage.py changepassword admin` |
| Rebuild après modif `.env` | `docker compose --profile prod down && docker compose --profile prod build backend-prod && docker compose --profile prod up -d` |
| Page blanche | Vider le cache navigateur (`Ctrl+Shift+R`) |

---

## 📋 Informations à conserver précieusement

```
🌐 URL publique (depuis partout) : https://TON_DOMAINE.ngrok-free.app
🏠 URL locale (WiFi mosquée)     : http://192.168.0.XX
🔧 Django Admin                  : http://192.168.0.XX/admin/
👤 Login app                     : admin / TON_MOT_DE_PASSE
🖥️  SSH Pi                       : ssh mosquee@192.168.0.XX
🔑 SSH password                  : Mosquee2026!
```

---

## 🏗️ Architecture technique

```
┌─────────────────────────────────────────────────────────────┐
│                      Raspberry Pi                            │
│                                                              │
│  ┌────────────┐   ┌─────────────┐   ┌────────────────────┐  │
│  │ PostgreSQL │   │   Gunicorn  │   │       Nginx        │  │
│  │    (db)    │◄──│ (backend)   │◄──│  port 80           │  │
│  └────────────┘   └─────────────┘   │  /api  → backend   │  │
│                                     │  /admin → backend   │  │
│  ┌──────────────────────────────┐   │  /     → index.html │  │
│  │  ngrok (service systemd)     │◄──└────────────────────┘  │
│  └──────────────────────────────┘                           │
└──────────────────┬──────────────────────────────────────────┘
                   │ tunnel HTTPS chiffré
         ┌─────────▼──────────┐
         │   ngrok Edge        │  HTTPS automatique
         └─────────┬───────────┘
                   │
         ┌─────────▼──────────────────────┐
         │  Utilisateurs partout           │
         │  https://xxx.ngrok-free.app     │
         └─────────────────────────────────┘
```

---

*Mosquée Manager — dernière mise à jour : mars 2026*
