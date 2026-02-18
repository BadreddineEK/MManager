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

echo "📁 Collecte des fichiers statiques..."
python manage.py collectstatic --noinput --clear

echo "🚀 Démarrage : $@"
exec "$@"
