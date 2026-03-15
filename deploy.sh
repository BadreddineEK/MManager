#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy.sh — Déploiement production Mosquée Manager
#             Raspberry Pi 4/5 + ngrok (accès depuis partout, gratuit)
#             Fonctionne aussi sur tout Linux x86 (PC, VPS)
#
# Usage :
#   chmod +x deploy.sh && ./deploy.sh
#
# Prérequis :
#   - Raspberry Pi OS / Ubuntu / Debian avec accès internet
#   - .env configuré (copier .env.example → .env)
#   - NGROK_AUTHTOKEN et NGROK_DOMAIN renseignés dans .env
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[ OK ]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERR ]${NC} $1"; exit 1; }

echo -e "${BOLD}"
echo "╔══════════════════════════════════════════════════╗"
echo "║   Mosquée Manager — Déploiement Production       ║"
echo "║   Raspberry Pi + ngrok                           ║"
echo "╚══════════════════════════════════════════════════╝"
echo -e "${NC}"

# ── 1. Installer Docker si absent ─────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    info "Docker non trouvé — installation automatique..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER"
    success "Docker installé"
    warn "Ferme et rouvre ta session SSH/terminal, puis relance ./deploy.sh"
    exit 0
fi
success "Docker $(docker --version | cut -d' ' -f3 | tr -d ',')"

# ── 2. Vérifications .env ──────────────────────────────────────────────────────
info "Vérification de la configuration..."

[ -f ".env" ] || error ".env introuvable. Copier .env.example → .env et le configurer."

# Charger le .env
set -a; source .env; set +a

# DEBUG doit être False
DEBUG_VAL=$(echo "${DJANGO_DEBUG:-true}" | tr '[:upper:]' '[:lower:]')
if [ "$DEBUG_VAL" != "false" ]; then
    warn "DJANGO_DEBUG n'est pas False dans .env !"
    read -rp "  Continuer quand même ? (oui/non) : " REPLY
    [[ "$REPLY" == "oui" ]] || error "Annulé. Mettre DJANGO_DEBUG=False dans .env."
fi

# ngrok
NGROK_TOKEN="${NGROK_AUTHTOKEN:-}"
NGROK_DOM="${NGROK_DOMAIN:-}"
if [ -z "$NGROK_TOKEN" ] || [ "$NGROK_TOKEN" = "CHANGE_MOI" ]; then
    warn "NGROK_AUTHTOKEN vide — accès depuis l'extérieur non configuré."
    SKIP_NGROK=true
else
    SKIP_NGROK=false
    success "Token ngrok détecté"
fi

success "Configuration OK"

# ── 3. Pull dernière version ──────────────────────────────────────────────────
info "Mise à jour du code (git pull)..."
git pull origin main 2>/dev/null || warn "git pull échoué (modifications locales ?)"
success "Code à jour ($(git log -1 --format='%h %s'))"

# ── 4. Build des images ───────────────────────────────────────────────────────
info "Build des images Docker (peut prendre 2-5 min sur Raspberry Pi)..."
docker compose --profile prod build
success "Images buildées"

# ── 5. Arrêt propre ───────────────────────────────────────────────────────────
info "Arrêt des anciens conteneurs..."
docker compose --profile prod down --remove-orphans 2>/dev/null || true

# ── 6. Démarrage ──────────────────────────────────────────────────────────────
info "Démarrage des services..."
docker compose --profile prod up -d
success "Services démarrés"

# ── 7. Migrations + collectstatic ─────────────────────────────────────────────
info "Attente que la base de données soit prête (30s max)..."
for i in $(seq 1 15); do
    if docker compose --profile prod exec -T db pg_isready -U mosque_user -d mosque_db &>/dev/null; then
        success "Base de données prête"; break
    fi
    [ $i -eq 15 ] && error "Base de données non disponible après 30s"
    sleep 2
done

info "Migrations Django..."
docker compose --profile prod exec -T backend-prod python manage.py migrate --noinput
success "Migrations OK"

info "Collecte des fichiers statiques..."
docker compose --profile prod exec -T backend-prod python manage.py collectstatic --noinput --clear
success "Fichiers statiques OK"

# ── 8. ngrok ──────────────────────────────────────────────────────────────────
if [ "$SKIP_NGROK" = false ]; then
    # Installer ngrok si absent
    if ! command -v ngrok &>/dev/null; then
        info "Installation de ngrok..."
        curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc \
            | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
        echo "deb https://ngrok-agent.s3.amazonaws.com buster main" \
            | sudo tee /etc/apt/sources.list.d/ngrok.list
        sudo apt-get update -qq && sudo apt-get install -y ngrok
        success "ngrok installé"
    fi

    # Configurer le token
    ngrok config add-authtoken "$NGROK_TOKEN" >/dev/null 2>&1
    success "ngrok configuré"

    # Créer/mettre à jour le service systemd
    if [ -n "$NGROK_DOM" ] && [ "$NGROK_DOM" != "ton-domaine.ngrok-free.app" ]; then
        NGROK_BIN=$(which ngrok)
        CURRENT_USER=$(whoami)
        sudo tee /etc/systemd/system/ngrok.service > /dev/null <<EOF
[Unit]
Description=ngrok tunnel — Mosquée Manager
After=network.target docker.service
Wants=docker.service

[Service]
ExecStart=${NGROK_BIN} http --url=${NGROK_DOM} 80
Restart=always
RestartSec=10
User=${CURRENT_USER}

[Install]
WantedBy=multi-user.target
EOF
        sudo systemctl daemon-reload
        sudo systemctl enable ngrok
        sudo systemctl restart ngrok
        success "Service ngrok activé → https://${NGROK_DOM}"
    else
        warn "NGROK_DOMAIN non défini — tunnel non démarré. Voir INSTALL.md."
    fi
fi

# ── 9. Health check ──────────────────────────────────────────────────────────
info "Health check nginx → backend..."
sleep 5
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/health/ 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    success "Health check OK (HTTP 200)"
else
    warn "Health check HTTP $HTTP_CODE — vérifier : docker compose --profile prod logs"
fi

# ── 10. Résumé final ──────────────────────────────────────────────────────────
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "inconnue")

echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║          Déploiement terminé ✅                   ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
docker compose --profile prod ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null || true
echo ""
echo -e "  ${BOLD}� Accès réseau local (WiFi mosquée) :${NC}"
echo -e "     http://${LOCAL_IP}"
echo -e "     http://${LOCAL_IP}/admin/   ← Django Admin"
echo ""
if [ "$SKIP_NGROK" = false ] && [ -n "$NGROK_DOM" ] && [ "$NGROK_DOM" != "ton-domaine.ngrok-free.app" ]; then
    echo -e "  ${BOLD}🌐 Accès depuis partout (ngrok) :${NC}"
    echo -e "     https://${NGROK_DOM}"
else
    echo -e "  ${YELLOW}🌐 Accès à distance non configuré.${NC}"
    echo -e "     → Définir NGROK_AUTHTOKEN et NGROK_DOMAIN dans .env"
    echo -e "     → Voir INSTALL.md section 'Accès depuis l'extérieur'"
fi
echo ""
echo -e "  ${BOLD}Commandes utiles :${NC}"
echo -e "  Logs live     : docker compose --profile prod logs -f"
echo -e "  Backup manuel : docker compose --profile prod run --rm backup"
echo -e "  Mise à jour   : ./deploy.sh"
echo -e "  Arrêt         : docker compose --profile prod down"
echo -e "  Statut ngrok  : sudo systemctl status ngrok"
echo ""
