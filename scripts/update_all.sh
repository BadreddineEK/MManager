#!/usr/bin/env bash
# ═════════════════════════════════════════════════════════════════════════════
#  update_all.sh — Mise à jour simultanée de toutes les instances mosquées
#
#  Usage :
#    chmod +x scripts/update_all.sh
#    ./scripts/update_all.sh
#
#  Configuration :
#    Renseigner la liste INSTANCES ci-dessous, ou créer un fichier
#    scripts/instances.conf (un "user@host nom_mosquee" par ligne)
#
#  Ce que fait ce script par instance :
#    1. git pull origin main
#    2. docker compose build backend-prod  (nouveau code)
#    3. docker compose up -d               (rolling restart, DB intacte)
#    4. manage.py migrate                  (nouvelles migrations seulement)
#    5. Rapport OK / ERREUR
#
#  Ce qui NE change JAMAIS lors d'une mise à jour :
#    - La base de données (volume Docker persistant)
#    - Le fichier .env (config/secrets spécifiques à l'instance)
#    - Les paramètres mosquée (MosqueSettings dans la DB)
# ═════════════════════════════════════════════════════════════════════════════

set -uo pipefail

# ── Couleurs ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
err()  { echo -e "  ${RED}✗${NC} $1"; }
info() { echo -e "  ${BLUE}→${NC} $1"; }

# ── Liste des instances ───────────────────────────────────────────────────────
# Format : "user@host NomMosquée"
# Charger depuis un fichier externe si disponible
INSTANCES_FILE="$(dirname "$0")/instances.conf"

if [ -f "$INSTANCES_FILE" ]; then
    mapfile -t INSTANCES < <(grep -v '^#' "$INSTANCES_FILE" | grep -v '^$')
else
    # ⚠️ Modifier cette liste avec vos instances
    INSTANCES=(
        "mosquee@192.168.0.13 Meximieux"
        # "mosquee@192.168.1.20 Lyon"
        # "mosquee@10.0.0.5    Paris"
    )
fi

# ── Variables de résultat ─────────────────────────────────────────────────────
SUCCESS_COUNT=0
FAIL_COUNT=0
declare -A RESULTS

# ── Fonction de mise à jour d'une instance ───────────────────────────────────
update_instance() {
    local CONNECTION="$1"
    local NAME="$2"
    local HOST="${CONNECTION#*@}"

    echo ""
    echo -e "${BOLD}━━━ $NAME ($HOST) ━━━${NC}"

    # Commande envoyée en SSH (une seule connexion pour tout)
    local CMD='
set -e
cd ~/MManager

echo "  → git pull"
git pull origin main 2>&1 | tail -3

echo "  → build"
docker compose --profile prod build backend-prod --quiet 2>&1 | tail -3

echo "  → restart"
docker compose --profile prod up -d --no-deps backend-prod 2>&1

echo "  → migrate"
sleep 3
docker compose --profile prod exec -T backend-prod \
    python manage.py migrate --noinput 2>&1 | tail -10

echo "  → check"
docker compose --profile prod exec -T backend-prod \
    python manage.py check --deploy 2>&1 | grep -E "issues|System"

echo "DONE_OK"
'

    local OUTPUT
    if OUTPUT=$(ssh -o ConnectTimeout=15 -o StrictHostKeyChecking=no \
        "$CONNECTION" "$CMD" 2>&1); then
        if echo "$OUTPUT" | grep -q "DONE_OK"; then
            ok "Mise à jour OK"
            RESULTS["$NAME"]="✅ OK"
            ((SUCCESS_COUNT++)) || true
        else
            err "Script terminé sans confirmation"
            echo "$OUTPUT" | tail -20
            RESULTS["$NAME"]="⚠️  Incomplet"
            ((FAIL_COUNT++)) || true
        fi
    else
        err "Connexion SSH échouée (hôte injoignable ou erreur)"
        RESULTS["$NAME"]="❌ SSH échoué"
        ((FAIL_COUNT++)) || true
    fi
}

# ── Exécution ─────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║   Mosquée Manager — Mise à jour multi-instances       ║${NC}"
echo -e "${BOLD}║   $(date '+%d/%m/%Y %H:%M:%S')                               ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Instances configurées : ${#INSTANCES[@]}${NC}"
for ENTRY in "${INSTANCES[@]}"; do
    read -r CONN NOM <<< "$ENTRY"
    echo "  • $NOM (${CONN#*@})"
done

echo ""
read -rp "$(echo -e "${YELLOW}Continuer la mise à jour ? (oui/non) : ${NC}")" CONFIRM
[[ "$CONFIRM" == "oui" ]] || { echo "Annulé."; exit 0; }

# Mise à jour séquentielle (évite les conflits de logs)
for ENTRY in "${INSTANCES[@]}"; do
    read -r CONN NOM <<< "$ENTRY"
    update_instance "$CONN" "$NOM"
done

# ── Rapport final ─────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}━━━ RAPPORT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
for NOM in "${!RESULTS[@]}"; do
    echo -e "  $NOM : ${RESULTS[$NOM]}"
done
echo ""
echo -e "  ${GREEN}Succès : $SUCCESS_COUNT${NC}   ${RED}Échecs : $FAIL_COUNT${NC}"
echo ""

[ "$FAIL_COUNT" -eq 0 ] && exit 0 || exit 1
