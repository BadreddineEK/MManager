#!/bin/sh
# ─────────────────────────────────────────────────────────────────────────────
# Script de sauvegarde — Mosquée Manager
# Lancé par le conteneur "backup" dans docker-compose (profil prod)
#
# Dépendances dans le conteneur : pg_dump (postgres image) + openssl
# Variables requises : DATABASE_URL, BACKUP_PASSPHRASE, BACKUP_TARGET
# Variables optionnelles (si BACKUP_TARGET=s3) : AWS_ACCESS_KEY_ID,
#   AWS_SECRET_ACCESS_KEY, AWS_BUCKET_NAME
# ─────────────────────────────────────────────────────────────────────────────

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"
BACKUP_FILE="${BACKUP_DIR}/mosque_backup_${TIMESTAMP}.sql"
ENCRYPTED_FILE="${BACKUP_FILE}.enc"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🔒 Démarrage de la sauvegarde (${TIMESTAMP})..."

# ── Extraction des paramètres depuis DATABASE_URL ─────────────────────────────
# Format : postgres://USER:PASSWORD@HOST:PORT/DBNAME
DB_USER=$(echo "$DATABASE_URL" | sed 's|postgres://||' | cut -d: -f1)
DB_PASS=$(echo "$DATABASE_URL" | sed 's|postgres://[^:]*:||' | cut -d@ -f1)
DB_HOST=$(echo "$DATABASE_URL" | cut -d@ -f2 | cut -d: -f1)
DB_PORT=$(echo "$DATABASE_URL" | cut -d@ -f2 | cut -d: -f2 | cut -d/ -f1)
DB_NAME=$(echo "$DATABASE_URL" | cut -d/ -f4)

# ── Dump PostgreSQL (format custom = restauration sélective possible) ─────────
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 📦 Dump PostgreSQL → ${BACKUP_FILE}..."
export PGPASSWORD="$DB_PASS"
pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --format=custom \
    --compress=9 \
    --file="$BACKUP_FILE"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ Dump créé ($(du -sh "$BACKUP_FILE" | cut -f1))"

# ── Chiffrement AES-256-CBC ───────────────────────────────────────────────────
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🔑 Chiffrement AES-256..."
openssl enc -aes-256-cbc -pbkdf2 -iter 100000 \
    -in  "$BACKUP_FILE" \
    -out "$ENCRYPTED_FILE" \
    -pass pass:"$BACKUP_PASSPHRASE"

# Suppression du dump non chiffré
rm -f "$BACKUP_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ Fichier chiffré : ${ENCRYPTED_FILE}"

# ── Stockage selon BACKUP_TARGET ──────────────────────────────────────────────
if [ "$BACKUP_TARGET" = "s3" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ☁️  Upload vers S3 (${AWS_BUCKET_NAME})..."
    # aws CLI doit être disponible dans l'image (à ajouter si BACKUP_TARGET=s3)
    aws s3 cp "$ENCRYPTED_FILE" "s3://${AWS_BUCKET_NAME}/$(basename "$ENCRYPTED_FILE")" \
        --storage-class STANDARD_IA
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ Upload S3 terminé."
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 💾 Sauvegarde locale conservée dans ${BACKUP_DIR}"
fi

# ── Rotation : garder uniquement les 30 dernières sauvegardes locales ─────────
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "mosque_backup_*.enc" -type f | wc -l)
if [ "$BACKUP_COUNT" -gt 30 ]; then
    find "$BACKUP_DIR" -name "mosque_backup_*.enc" -type f \
        | sort \
        | head -n -30 \
        | xargs rm -f
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🧹 Rotation effectuée (conservation: 30 derniers backups)"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ Sauvegarde terminée avec succès."
echo ""
echo "── Restore (si nécessaire) ──────────────────────────────────────────────"
echo "  # Déchiffrement :"
echo "  openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 \\"
echo "    -in  mosque_backup_YYYYMMDD_HHMMSS.sql.enc \\"
echo "    -out restore.sql -pass pass:\$BACKUP_PASSPHRASE"
echo ""
echo "  # Restauration :"
echo "  pg_restore -h HOST -U USER -d mosque_db --clean restore.sql"
echo "──────────────────────────────────────────────────────────────────────────"
