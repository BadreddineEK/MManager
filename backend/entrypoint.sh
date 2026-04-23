#!/bin/sh
# entrypoint.sh — attend DB -> migrate -> init tenant public -> collectstatic -> start

set -e

echo "Attente de la base de donnees PostgreSQL..."
python manage.py wait_for_db

echo "Application des migrations Django..."
python manage.py migrate --noinput

echo "Initialisation du tenant public..."
python manage.py shell << 'PYEOF'
from core.models import Mosque, Domain
pub, created = Mosque.objects.get_or_create(
    schema_name='public',
    defaults={'name': 'Public', 'slug': 'public'}
)
if created:
    print('  Tenant public cree')
Domain.objects.get_or_create(
    domain='localhost',
    defaults={'tenant': pub, 'is_primary': True}
)
print('  Domaine localhost OK')
PYEOF

echo "Collecte des fichiers statiques..."
python manage.py collectstatic --noinput --clear

echo "Demarrage : $@"
exec "$@"
