#!/usr/bin/env python
"""Utilitaire de ligne de commande Django pour les tâches administratives."""
import os
import sys


def main() -> None:
    """Lance les tâches administratives Django."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Impossible d'importer Django. Vérifiez que Django est installé "
            "et disponible dans votre PYTHONPATH. Avez-vous oublié d'activer "
            "un virtualenv ou d'installer les dépendances (pip install -r requirements.txt) ?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
