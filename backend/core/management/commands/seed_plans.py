from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context

PLANS_CONFIG = [
    {"name": "free_cloud", "display_name": "Nidham Free", "description": "Tresorerie basique et portail public.", "price_monthly": "0.00", "price_yearly": "0.00", "max_families": 30, "max_users": 1, "max_sms_month": 0, "modules": ["core", "public_portal"], "is_active": True, "is_public": True, "sort_order": 0},
    {"name": "standard", "display_name": "Nidham Standard", "description": "Tresorerie complete, ecole basique, portail public.", "price_monthly": "39.00", "price_yearly": "390.00", "max_families": 100, "max_users": 5, "max_sms_month": 0, "modules": ["core", "treasury_full", "school_basic", "public_portal", "email_groups"], "is_active": True, "is_public": True, "sort_order": 1},
    {"name": "pro", "display_name": "Nidham Pro", "description": "Tout Standard + ecole complete, SMS, portail famille, analytics.", "price_monthly": "79.00", "price_yearly": "790.00", "max_families": -1, "max_users": -1, "max_sms_month": 150, "modules": ["core", "treasury_full", "treasury_fec", "school_basic", "school_full", "public_portal", "email_groups", "sms", "member_portal", "analytics", "mobile_app"], "is_active": True, "is_public": True, "sort_order": 2},
    {"name": "federation", "display_name": "Nidham Federation", "description": "Tout Pro + dashboard federal multi-sites. Sur devis.", "price_monthly": "199.00", "price_yearly": "1990.00", "max_families": -1, "max_users": -1, "max_sms_month": 500, "modules": ["core", "treasury_full", "treasury_fec", "school_basic", "school_full", "public_portal", "email_groups", "sms", "member_portal", "analytics", "mobile_app", "federation"], "is_active": True, "is_public": False, "sort_order": 3},
]

class Command(BaseCommand):
    help = "Cree ou met a jour les 4 plans Nidham. Modifier PLANS_CONFIG pour changer prix/modules."
    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true")
    def handle(self, *args, **options):
        force = options["force"]
        with schema_context("public"):
            from core.models import Plan
            created = updated = 0
            for cfg in PLANS_CONFIG:
                plan, is_new = Plan.objects.get_or_create(name=cfg["name"], defaults=cfg)
                if is_new:
                    created += 1
                    self.stdout.write(self.style.SUCCESS(f"  Cree: {plan}"))
                elif force:
                    [setattr(plan, k, v) for k, v in cfg.items()]
                    plan.save()
                    updated += 1
                    self.stdout.write(self.style.WARNING(f"  MAJ: {plan}"))
                else:
                    self.stdout.write(f"  Existe: {plan}")
            legacy = Plan.objects.filter(name__in=["free","starter","premium","promo_test","ramadan_promo"])
            if legacy.exists():
                names = list(legacy.values_list("name", flat=True))
                legacy.update(is_active=False, is_public=False)
                self.stdout.write(self.style.WARNING(f"  Desactives: {names}"))
            self.stdout.write(self.style.SUCCESS(f"seed_plans OK: {created} crees, {updated} MAJ"))