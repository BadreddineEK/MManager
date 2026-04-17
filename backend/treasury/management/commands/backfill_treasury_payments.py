"""
Commande de backfill : cree les TreasuryTransactions manquantes
pour les SchoolPayments et MembershipPayments existants (crees avant les signaux).

Usage:
    python manage.py backfill_treasury_payments [--dry-run]
    python manage.py backfill_treasury_payments --schema mosquee_alpha
"""
from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import get_tenant_model, schema_context


class Command(BaseCommand):
    help = "Backfill TreasuryTransactions for existing SchoolPayments and MembershipPayments"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Ne rien ecrire, juste compter")
        parser.add_argument("--schema", default=None, help="Schema specifique (defaut: tous les tenants)")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        target_schema = options["schema"]

        Mosque = get_tenant_model()
        if target_schema:
            mosques = Mosque.objects.filter(schema_name=target_schema)
        else:
            mosques = Mosque.objects.exclude(schema_name="public")

        if not mosques.exists():
            raise CommandError("Aucun tenant trouve.")

        for mosque in mosques:
            self.stdout.write(f"\n=== Schema: {mosque.schema_name} ({mosque.name}) ===")
            with schema_context(mosque.schema_name):
                self._backfill_school(mosque, dry_run)
                self._backfill_membership(mosque, dry_run)

    def _backfill_school(self, mosque, dry_run):
        from school.models import SchoolPayment
        from treasury.models import TreasuryTransaction

        created = 0
        skipped = 0
        for payment in SchoolPayment.objects.filter(mosque=mosque):
            # Passer les virements
            if payment.method == "virement":
                skipped += 1
                continue
            # Verifier si deja une TreasuryTx liee
            try:
                _ = payment.treasury_tx
                skipped += 1
                continue
            except Exception:
                pass

            # Construire le label
            child = payment.child
            year = payment.school_year.label if payment.school_year else ""
            if child:
                label = f"Ecole - {child.first_name} {payment.family.primary_contact_name} ({year})"
            else:
                label = f"Ecole - {payment.family.primary_contact_name} ({year})"

            if not dry_run:
                TreasuryTransaction.objects.create(
                    mosque=mosque,
                    date=payment.date,
                    category="ecole",
                    label=label,
                    direction="IN",
                    amount=payment.amount,
                    method=payment.method,
                    source="cash_school",
                    import_status="validated",
                    note=payment.note or "",
                    family=payment.family,
                    school_year=payment.school_year,
                    school_payment=payment,
                )
            created += 1

        self.stdout.write(f"  SchoolPayment: {created} crees, {skipped} ignores" + (" [DRY RUN]" if dry_run else ""))

    def _backfill_membership(self, mosque, dry_run):
        from membership.models import MembershipPayment
        from treasury.models import TreasuryTransaction

        created = 0
        skipped = 0
        for payment in MembershipPayment.objects.filter(mosque=mosque):
            if payment.method == "virement":
                skipped += 1
                continue
            try:
                _ = payment.treasury_tx
                skipped += 1
                continue
            except Exception:
                pass

            year = payment.membership_year.year if payment.membership_year else ""
            label = f"Cotisation {year} - {payment.member.full_name}"

            if not dry_run:
                TreasuryTransaction.objects.create(
                    mosque=mosque,
                    date=payment.date,
                    category="cotisation",
                    label=label,
                    direction="IN",
                    amount=payment.amount,
                    method=payment.method,
                    source="cash_cotis",
                    import_status="validated",
                    note=payment.note or "",
                    member=payment.member,
                    membership_year=payment.membership_year,
                    membership_payment=payment,
                )
            created += 1

        self.stdout.write(f"  MembershipPayment: {created} crees, {skipped} ignores" + (" [DRY RUN]" if dry_run else ""))
