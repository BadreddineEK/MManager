#!/bin/bash
# deploy_dev.sh — Push Mac → GitHub → Pull Pi → Restart backend
# Usage: ./scripts/deploy_dev.sh "message de commit"

set -e
MSG="${1:-wip}"

echo "📦 Commit & push Mac → GitHub..."
cd "$(git rev-parse --show-toplevel)"
git add -A
git commit -m "$MSG" || echo "(rien à committer)"
git push origin feature/multi-tenant-saas

echo "🔄 Pull Pi + restart backend..."
ssh mosquee@192.168.0.14 "
  cd ~/nidham-dev &&
  git pull origin feature/multi-tenant-saas &&
  docker compose -f docker-compose.dev.yml restart backend_dev &&
  echo '✅ Pi à jour'
"
