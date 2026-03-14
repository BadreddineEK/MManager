#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy.sh — Déploiement production Mosquée Manager
#
# Usage :
#   chmod +x deploy.sh
#   ./deploy.sh
#
# Prérequis :
#   - Docker + Docker Compose installés
#   - .env configuré (copier .env.example → .env et adapter)
#   - CLOUDFLARE_TUNNEL_TOKEN renseigné dans .env
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC}   $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERR]${NC}  $1"; exit 1; }

echo -e "${BOLD}"
echo "╔══════════════════════════════════════════════╗"
echo "║    Mosquée Manager — Déploiement Production  ║"
echo "╚══════════════════════════════════════════════╝"
echo -e "${NC}"

# ── 1. Vérifications préalables ───────────────────────────────────────────────
info "Vérification des prérequis..."

command -v docker  >/dev/null 2>&1 || error "Docker n'est pas installé."
command -v git     >/dev/null 2>&1 || error "Git n'est pas installé."

[ -f ".env" ] || error "Fichier .env introuvable. Copier .env.example → .env et le configurer."

# Vérifie que DEBUG=False
DEBUG_VAL=$(grep -E '^DJANGO_DEBUG=' .env | cut -d= -f2 | tr -d '[:space:]' | tr '[:upper:]' '[:lower:]')
if [ "$DEBUG_VAL" != "false" ]; then
    warn "DJANGO_DEBUG n'est pas False dans .env."
    read -rp "Continuer quand même ? (oui/non) : " REPLY
    [[ "$REPLY" == "oui" ]] || error "Déploiement annulé. Mettre DJANGO_DEBUG=False dans .env."
fi

# Vérifie le tunnel Cloudflare
CF_TOKEN=$(grep -E '^CLOUDFLARE_TUNNEL_TOKEN=' .env | cut -d= -f2 | tr -d '[:space:]')
if [ -z "$CF_TOKEN" ]; then
    warn "CLOUDFLARE_TUNNEL_TOKEN est vide dans .env."
    warn "Le service cloudflared ne sera pas démarré."
    SKIP_CLOUDFLARE=true
else
    SKIP_CLOUDFLARE=false
fi

success "Prérequis OK"

# ── 2. Pull dernière version ──────────────────────────────────────────────────
info "Récupération de la dernière version (git pull)..."
git pull origin main
success "Code à jour"

# ── 3. Build des images ───────────────────────────────────────────────────────
info "Build des images Docker..."
docker compose --profile prod build --no-cache
success "Images buildées"

# ── 4. Arrêt des anciens conteneurs ──────────────────────────────────────────
info "Arrêt des anciens conteneurs..."
docker compose --profile prod down --remove-orphans 2>/dev/null || true
success "Anciens conteneurs arrêtés"

# ── 5. Démarrage (sans cloudflared si token absent) ──────────────────────────
if [ "$SKIP_CLOUDFLARE" = true ]; then
    info "Démarrage sans Cloudflare Tunnel..."
    docker compose --profile prod up -d --scale cloudflared=0 2>/dev/null || \
    docker compose up -d db backend-prod nginx
else
    info "Démarrage complet (avec Cloudflare Tunnel)..."
    docker compose --profile prod up -d
fi
success "Conteneurs démarrés"

# ── 6. Migrations + collectstatic ─────────────────────────────────────────────
info "Attente que le backend soit prêt..."
sleep 5

info "Migrations Django..."
docker compose --profile prod exec -T backend-prod python manage.py migrate --noinput
success "Migrations OK"

info "Collecte des fichiers statiques..."
docker compose --profile prod exec -T backend-prod python manage.py collectstatic --noinput
success "Fichiers statiques OK"

# ── 7. Health check ──────────────────────────────────────────────────────────
info "Health check..."
sleep 3
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/health/ 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    success "Health check OK (HTTP 200)"
else
    warn "Health check retourné HTTP $HTTP_CODE (le tunnel démarre peut-être encore)"
fi

# ── 8. Résumé ─────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║          Déploiement terminé ✅               ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}Services actifs :${NC}"
docker compose --profile prod ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || docker compose ps
echo ""
if [ "$SKIP_CLOUDFLARE" = false ]; then
    echo -e "  ${BOLD}🌐 L'app est accessible via votre tunnel Cloudflare.${NC}"
    echo -e "  Vérifier sur : https://one.dash.cloudflare.com → Zero Trust → Tunnels"
else
    echo -e "  ${YELLOW}⚠️  Cloudflare Tunnel non configuré.${NC}"
    echo -e "  L'app tourne localement sur http://localhost:80"
    echo -e "  Pour exposer sur internet : configurer CLOUDFLARE_TUNNEL_TOKEN dans .env"
fi
echo ""
echo -e "  ${BOLD}Commandes utiles :${NC}"
echo -e "  Logs backend  : docker compose --profile prod logs -f backend-prod"
echo -e "  Logs nginx    : docker compose --profile prod logs -f nginx"
echo -e "  Backup manuel : docker compose --profile prod run --rm backup"
echo -e "  Arrêt         : docker compose --profile prod down"
echo ""
