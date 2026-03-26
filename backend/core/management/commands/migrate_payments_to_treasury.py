"""
Management command : migrate_payments_to_treasury
==================================================
Migre les SchoolPayment et MembershipPayment existants
vers des TreasuryTransaction (avec FK family/member).

Usage :
    python manage.py migrate_payments_to_treasury [--dry-run] [--mosque-id N]

Idempotent : un paiement déjà migré (même montant + date + famille/membre)
ne sera pas dupliqué.
"""
from django.core.management.base import BaseCommand
from django.db import transaction as db_transaction

from school.models import SchoolPayment
from membership.models import MembershipPayment
from treasury.models import TreasuryTransaction


class Command(BaseCommand):
    help = "Migre SchoolPayment et MembershipPayment vers TreasuryTransaction"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Simulation sans modification")
        parser.add_argument("--mosque-id", type=int, default=None, help="Limiter à une mosquée")

    def handle(self, *args, **options):
        dry_run   = options["dry_run"]
        mosque_id = options["mosque_id"]

        school_qs = SchoolPayment.objects.select_related(
            "mosque", "family", "child", "school_year"
        )
        member_qs = MembershipPayment.objects.select_related(
            "mosque", "member", "membership_year"
        )

        if mosque_id:
            school_qs  = school_qs.filter(mosque_id=mosque_id)
            member_qs  = member_qs.filter(mosque_id=mosque_id)

        school_count  = school_qs.count()
        member_count  = member_qs.count()
        self.stdout.write(f"À migrer : {school_count} paiements école, {member_count} cotisations")

        if dry_run:
            self.stdout.write(self.style.WARNING("-- DRY RUN : aucune modification --"))

        created_school  = 0
        skipped_school  = 0
        created_member  = 0
        skipped_member  = 0

        with db_transaction.atomic():

            # ── Paiements école ────────────────────────────────────────────
            for sp in school_qs:
                child_label = f" ({sp.child.first_name})" if sp.child else ""
                label = f"École coranique — {sp.family.primary_contact_name}{child_label}"

                # Idempotence : existe déjà ?
                exists = TreasuryTransaction.objects.filter(
                    mosque=sp.mosque,
                    category="ecole",
                    date=sp.date,
                    amount=sp.amount,
                    family=sp.family,
                    school_year=sp.school_year,
                ).exists()

                if exists:
                    skipped_school += 1
                    continue

                if not dry_run:
                    TreasuryTransaction.objects.create(
                        mosque        = sp.mosque,
                        date          = sp.date,
                        category      = "ecole",
                        label         = label,
                        direction     = TreasuryTransaction.DIRECTION_IN,
                        amount        = sp.amount,
                        method        = sp.method,
                        note          = sp.note,
                        regime_fiscal = "",
                        family        = sp.family,
                        school_year   = sp.school_year,
                    )
                created_school += 1

            # ── Cotisations adhérents ──────────────────────────────────────
            for mp in member_qs:
                label = f"Cotisation — {mp.member.full_name} ({mp.membership_year.year})"

                exists = TreasuryTransaction.objects.filter(
                    mosque=mp.mosque,
                    category="cotisation",
                    date=mp.date,
                    amount=mp.amount,
                    member=mp.member,
                    membership_year=mp.membership_year,
                ).exists()

                if exists:
                    skipped_member += 1
                    continue

                if not dry_run:
                    TreasuryTransaction.objects.create(
                        mosque          = mp.mosque,
                        date            = mp.date,
                        category        = "cotisation",
                        label           = label,
                        direction       = TreasuryTransaction.DIRECTION_IN,
                        amount          = mp.amount,
                        method          = mp.method,
                        note            = mp.note,
                        regime_fiscal   = "",
                        member          = mp.member,
                        membership_year = mp.membership_year,
                    )
                created_member += 1

        self.stdout.write(self.style.SUCCESS(
            f"École   : {created_school} créées, {skipped_school} déjà présentes"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"Cotis.  : {created_member} créées, {skipped_member} déjà présentes"
        ))
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run terminé — rien n'a été modifié"))
