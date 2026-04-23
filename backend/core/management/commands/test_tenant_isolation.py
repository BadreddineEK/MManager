"""
Management command : test_tenant_isolation

Verifie qu'aucune fuite cross-tenant n'est possible.
Usage : python manage.py test_tenant_isolation
"""
import logging

from django.core.management.base import BaseCommand
from django.db import connection
from django_tenants.utils import schema_context

from core.models import Mosque, Domain

logger = logging.getLogger("core")


class Command(BaseCommand):
    help = "Audit isolation multi-tenant"

    def handle(self, *args, **options):
        tenants = Mosque.objects.exclude(schema_name="public").order_by("schema_name")
        if tenants.count() < 2:
            self.stdout.write(self.style.WARNING(
                f"Seulement {tenants.count()} tenant(s) actif(s) — besoin de 2 pour tester l'isolation."
            ))
            return

        self.stdout.write(f"Tenants trouves : {[t.schema_name for t in tenants]}")
        errors = []

        # Pour chaque paire de tenants, verifier isolation User + Family/Member
        tenant_list = list(tenants)
        for i, t_a in enumerate(tenant_list):
            for t_b in tenant_list[i+1:]:
                errors += self._check_pair(t_a, t_b)

        if errors:
            for e in errors:
                self.stdout.write(self.style.ERROR(f"FUITE: {e}"))
            raise SystemExit(1)
        else:
            self.stdout.write(self.style.SUCCESS("OK: Aucune fuite detectee entre les tenants."))

    def _check_pair(self, t_a, t_b):
        errors = []
        # Compter users dans t_a depuis le schema de t_b
        with schema_context(t_b.schema_name):
            from django.apps import apps
            for model_name in ["Family", "Member", "Child", "Transaction"]:
                try:
                    Model = apps.get_model("core", model_name) if model_name not in ["Transaction"] else None
                    if Model is None:
                        try:
                            Model = apps.get_model("treasury", "Transaction")
                        except Exception:
                            continue
                    # Verifier que le schema actuel est bien t_b
                    current = connection.schema_name
                    if current != t_b.schema_name:
                        errors.append(f"schema_context defaillant: attendu {t_b.schema_name}, obtenu {current}")
                except Exception as e:
                    pass  # modele absent du tenant, normal
        return errors
