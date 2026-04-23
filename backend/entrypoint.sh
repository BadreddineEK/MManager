#!/bin/sh
# ─────────────────────────────────────────────────────────────────────────────
# Entrypoint du conteneur backend
# Ordre : attend la DB → migrations → démarrage du serveur
# ─────────────────────────────────────────────────────────────────────────────

set -e

echo "⏳ Attente de la base de données PostgreSQL..."
python manage.py wait_for_db

echo "📦 Application des migrations Django..."
python manage.py migrate --noinput


echo "Initialisation du tenant public..."
python manage.py shell -c "
from core.models import Mosque, Domain
pub, _ = Mosque.objects.get_or_create(schema_name="public", defaults={"name": "Public", "slug": "public"})
Domain.objects.get_or_create(domain="localhost", defaults={"tenant": pub, "is_primary": True})
print("Tenant public OK")
"
echo "📁 Collecte des fichiers statiques..."
python manage.py collectstatic --noinput --clear

echo "🚀 Démarrage : $@"
exec "$@"
