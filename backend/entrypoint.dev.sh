#!/bin/sh
# Entrypoint DEV - multi-tenant (django-tenants)
set -e
echo "Attente de la base de données..."
python manage.py wait_for_db
echo "Migrations schéma public (shared)..."
python manage.py migrate_schemas --shared --noinput
echo "Migrations tous les schémas tenant..."
python manage.py migrate_schemas --noinput
echo "Démarrage : $@"
exec "$@"
