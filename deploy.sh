#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy.sh — Déploiement production Mosquée Manager
#             Raspberry Pi 4/5 + Cloudflare Tunnel (Option C)
#             Fonctionne aussi sur tout Linux x86 (PC, VPS)
#
# Usage :
#   chmod +x deploy.sh && ./deploy.sh
#
# Prérequis :
#   - Raspberry Pi OS / Ubuntu / Debian avec accès internet
#   - .env configuré (copier .env.example → .env)
#   - CLOUDFLARE_TUNNEL_TOKEN renseigné dans .env
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
echo "║   Raspberry Pi + Cloudflare Tunnel               ║"
echo "╚══════════════════════════════════════════════════╝"
echo -e "${NC}"

# ── 1. Installer Docker si absent ─────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    info "Docker non trouvé — installation automatique..."
    curl -fsSL https://get.docker.com | sh
    # Ajouter l'utilisateur courant au groupe docker (évite sudo)
    sudo usermod -aG docker "$USER"
    success "Docker installé"
    warn "Ferme et rouvre ta session SSH/terminal, puis relance ./deploy.sh"
    exit 0
fi
success "Docker $(docker --version | cut -d' ' -f3 | tr -d ',')"

# ── 2. Vérifications .env ──────────────────────────────────────────────────────
info "Vérification de la configuration..."

[ -f ".env" ] || error ".env introuvable. Copier .env.example → .env et le configurer."

# DEBUG doit être False
DEBUG_VAL=$(grep -E '^DJANGO_DEBUG=' .env | cut -d= -f2 | tr -d '[:space:]' | tr '[:upper:]' '[:lower:]')
if [ "$DEBUG_VAL" != "false" ]; then
    warn "DJANGO_DEBUG n'est pas False dans .env !"
    warn "L'app va tourner en mode DEBUG — à corriger pour la prod."
    read -rp "  Continuer quand même ? (oui/non) : " REPLY
    [[ "$REPLY" == "oui" ]] || error "Annulé. Mettre DJANGO_DEBUG=False dans .env."
fi

# Token Cloudflare
CF_TOKEN=$(grep -E '^CLOUDFLARE_TUNNEL_TOKEN=' .env | cut -d= -f2 | tr -d '[:space:]')
if [ -z "$CF_TOKEN" ]; then
    warn "CLOUDFLARE_TUNNEL_TOKEN vide — l'app sera accessible sur le réseau local uniquement."
    warn "Voir INSTALL.md section 'Cloudflare Tunnel' pour l'activer."
    SKIP_CF=true
else
    SKIP_CF=false
    success "Token Cloudflare détecté"
fi

success "Configuration OK"

# ── 3. Pull dernière version ──────────────────────────────────────────────────
info "Mise à jour du code (git pull)..."
git pull origin main
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
info "Attente que le backend soit prêt (30s max)..."
for i in $(seq 1 12); do
    if docker compose --profile prod exec -T backend-prod python manage.py check --deploy &>/dev/null 2>&1; then
        break
    fi
    sleep 2
done

info "Migrations Django..."
docker compose --profile prod exec -T backend-prod python manage.py migrate --noinput
success "Migrations OK"

info "Collecte des fichiers statiques..."
docker compose --profile prod exec -T backend-prod python manage.py collectstatic --noinput --clear
success "Fichiers statiques OK"

# ── 8. Health check ──────────────────────────────────────────────────────────
info "Health check nginx → backend..."
sleep 3
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/health/ 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    success "Health check OK (HTTP 200)"
else
    warn "Health check HTTP $HTTP_CODE — vérifier les logs : docker compose --profile prod logs nginx"
fi

# ── 9. IP locale ──────────────────────────────────────────────────────────────
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "inconnue")

# ── 10. Résumé final ──────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║          Déploiement terminé ✅                   ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
docker compose --profile prod ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null || true
echo ""
echo -e "  ${BOLD}🌐 Accès réseau local (WiFi mosquée) :${NC}"
echo -e "     http://${LOCAL_IP}"
echo ""
if [ "$SKIP_CF" = false ]; then
    echo -e "  ${BOLD}☁️  Accès depuis n'importe où (Cloudflare) :${NC}"
    echo -e "     Voir l'URL sur https://one.dash.cloudflare.com → Zero Trust → Tunnels"
else
    echo -e "  ${YELLOW}☁️  Accès à distance non configuré.${NC}"
    echo -e "     → Voir INSTALL.md section 4 pour ajouter le tunnel Cloudflare."
fi
echo ""
echo -e "  ${BOLD}Commandes utiles :${NC}"
echo -e "  Logs live     : docker compose --profile prod logs -f"
echo -e "  Backup manuel : docker compose --profile prod run --rm backup"
echo -e "  Mise à jour   : ./deploy.sh"
echo -e "  Arrêt         : docker compose --profile prod down"
echo ""
