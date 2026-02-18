"""
Commande de gestion : wait_for_db
==================================
Bloque le démarrage jusqu'à ce que PostgreSQL soit prêt à accepter des connexions.
Utilisée dans entrypoint.sh avant d'appliquer les migrations.

Usage :
    python manage.py wait_for_db
    python manage.py wait_for_db --max-retries 60 --delay 1
"""
import logging
import time
from typing import Any

from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Attend que la base de données PostgreSQL soit disponible."""

    help = "Attend que la base de données soit prête à accepter des connexions."

    def add_arguments(self, parser: Any) -> None:
        """Arguments optionnels pour contrôler les tentatives."""
        parser.add_argument(
            "--max-retries",
            type=int,
            default=30,
            help="Nombre maximum de tentatives avant abandon (défaut: 30).",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=2.0,
            help="Délai en secondes entre chaque tentative (défaut: 2s).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Boucle de tentatives de connexion à la base de données."""
        max_retries: int = options["max_retries"]
        delay: float = options["delay"]

        self.stdout.write("⏳ Attente de la base de données PostgreSQL...")
        logger.info("Attente de la base de données (max %d tentatives).", max_retries)

        for attempt in range(1, max_retries + 1):
            try:
                # Vérifie la connexion à la base de données par défaut
                conn = connections["default"]
                conn.ensure_connection()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Base de données disponible ! (tentative {attempt}/{max_retries})"
                    )
                )
                logger.info("Base de données disponible après %d tentative(s).", attempt)
                return

            except OperationalError as exc:
                self.stdout.write(
                    f"  ⚠️  DB indisponible (tentative {attempt}/{max_retries}) — "
                    f"{exc!s:.80} — attente {delay}s..."
                )
                logger.warning(
                    "DB indisponible (tentative %d/%d) : %s",
                    attempt,
                    max_retries,
                    exc,
                )
                time.sleep(delay)

        # Toutes les tentatives épuisées
        error_msg = (
            f"❌ Impossible de se connecter à la base de données "
            f"après {max_retries} tentatives."
        )
        self.stderr.write(self.style.ERROR(error_msg))
        logger.error(error_msg)
        raise SystemExit(1)
