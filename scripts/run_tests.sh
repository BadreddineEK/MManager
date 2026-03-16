#!/bin/bash
# =============================================================================
# run_tests.sh — Lancer la suite de tests avant un déploiement
# =============================================================================
# Usage :
#   ./scripts/run_tests.sh            → tous les tests
#   ./scripts/run_tests.sh school     → tests d'une app seulement
#
# Retourne 0 si tout passe, 1 sinon (bloquant dans une CI ou un hook git)

set -euo pipefail

APP=${1:-""}
cd "$(dirname "$0")/.."

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║        🧪  MManager — Pile de tests automatisés     ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Vérifie que le conteneur backend est bien lancé
if ! docker compose ps backend | grep -q "running"; then
    echo "❌  Le conteneur backend n'est pas lancé."
    echo "    Lance d'abord : docker compose up -d"
    exit 1
fi

if [ -n "$APP" ]; then
    echo "▶  Tests : app '$APP'"
    CMD="pytest ${APP}/tests.py -v --tb=short -q"
else
    echo "▶  Tests : toutes les apps"
    CMD="pytest --tb=short -q"
fi

echo ""
docker compose exec -T backend bash -c "$CMD"
EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅  Tous les tests sont au vert — déploiement autorisé."
else
    echo "❌  Des tests ont échoué — NE PAS déployer."
fi
echo ""
exit $EXIT_CODE
