"""
Commande de migration de données — fix_mosque2_years
======================================================
Associe les paiements de cotisation et de scolarité de la mosquée 2
à leurs années correspondantes (SchoolYear / MembershipYear) quand
l'association est manquante ou pointe vers une année d'une autre mosquée.

Usage :
    python manage.py fix_mosque2_years --mosque-id 2 --dry-run
    python manage.py fix_mosque2_years --mosque-id 2

L'algorithme :
  1. Pour chaque MembershipPayment de la mosquée, si son membership_year
     appartient à une AUTRE mosquée → trouve l'année correspondante dans la
     mosquée cible par l'année calendaire (year field). Si aucune n'existe,
     prend l'année active ou la plus récente de la mosquée cible.
  2. Idem pour SchoolPayment / school_year.
"""
import logging

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

logger = logging.getLogger("core")


class Command(BaseCommand):
    help = "Réassocie les paiements de cotisation/scolarité à la bonne mosquée."

    def add_arguments(self, parser):
        parser.add_argument(
            "--mosque-id", type=int, required=True,
            help="ID de la mosquée à corriger (ex: 2)",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Affiche ce qui serait modifié sans sauvegarder",
        )

    def handle(self, *args, **options):
        from core.models import Mosque
        from membership.models import MembershipPayment, MembershipYear
        from school.models import SchoolPayment, SchoolYear

        mosque_id = options["mosque_id"]
        dry_run   = options["dry_run"]

        try:
            mosque = Mosque.objects.get(pk=mosque_id)
        except Mosque.DoesNotExist:
            raise CommandError(f"Mosquée id={mosque_id} introuvable.")

        self.stdout.write(f"\n{'[DRY-RUN] ' if dry_run else ''}Correction des années pour : {mosque.name}\n")

        # ── Membership payments ───────────────────────────────────────────────
        wrong_mp = MembershipPayment.objects.filter(mosque=mosque).exclude(
            membership_year__mosque=mosque
        ).select_related("membership_year")

        self.stdout.write(f"  MembershipPayments avec mauvaise année : {wrong_mp.count()}")

        # Années de la mosquée cible, indexées par year
        mp_years_by_year = {
            my.year: my for my in MembershipYear.objects.filter(mosque=mosque)
        }
        active_mp_year = MembershipYear.objects.filter(mosque=mosque, is_active=True).first()
        fallback_mp_year = MembershipYear.objects.filter(mosque=mosque).order_by("-year").first()

        mp_fixed = 0
        mp_missing_year = set()
        for pmt in wrong_mp:
            calendar_year = pmt.date.year
            target_year = (
                mp_years_by_year.get(calendar_year)
                or mp_years_by_year.get(calendar_year + 1)   # cotisation souvent de l'année N+1
                or active_mp_year
                or fallback_mp_year
            )
            if target_year is None:
                mp_missing_year.add(calendar_year)
                continue
            self.stdout.write(
                f"    [{pmt.id}] {pmt.member} | date={pmt.date} | "
                f"{pmt.membership_year} → {target_year}"
            )
            if not dry_run:
                pmt.membership_year = target_year
                pmt.save(update_fields=["membership_year"])
            mp_fixed += 1

        if mp_missing_year:
            self.stdout.write(
                self.style.WARNING(
                    f"  ⚠️  Aucune MembershipYear trouvée pour les années : {sorted(mp_missing_year)}"
                )
            )

        # ── School payments ───────────────────────────────────────────────────
        wrong_sp = SchoolPayment.objects.filter(mosque=mosque).exclude(
            school_year__mosque=mosque
        ).select_related("school_year")

        self.stdout.write(f"  SchoolPayments avec mauvaise année : {wrong_sp.count()}")

        sy_by_label = {
            sy.label: sy for sy in SchoolYear.objects.filter(mosque=mosque)
            if hasattr(sy, "label")
        }
        sy_by_start_year = {}
        for sy in SchoolYear.objects.filter(mosque=mosque):
            if sy.start_date:
                sy_by_start_year[sy.start_date.year] = sy
        active_sy = SchoolYear.objects.filter(mosque=mosque, is_active=True).first()
        fallback_sy = SchoolYear.objects.filter(mosque=mosque).order_by("-start_date").first()

        sp_fixed = 0
        sp_missing_year = set()
        for pmt in wrong_sp:
            cal_year = pmt.date.year
            target_sy = (
                sy_by_start_year.get(cal_year)
                or sy_by_start_year.get(cal_year - 1)
                or active_sy
                or fallback_sy
            )
            if target_sy is None:
                sp_missing_year.add(cal_year)
                continue
            self.stdout.write(
                f"    [{pmt.id}] {pmt.child if hasattr(pmt, 'child') else pmt} | "
                f"date={pmt.date} | {pmt.school_year} → {target_sy}"
            )
            if not dry_run:
                pmt.school_year = target_sy
                pmt.save(update_fields=["school_year"])
            sp_fixed += 1

        if sp_missing_year:
            self.stdout.write(
                self.style.WARNING(
                    f"  ⚠️  Aucune SchoolYear trouvée pour les années : {sorted(sp_missing_year)}"
                )
            )

        # ── Résumé ────────────────────────────────────────────────────────────
        self.stdout.write("")
        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"[DRY-RUN] {mp_fixed} cotisations + {sp_fixed} scolarités seraient corrigées."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"✅  {mp_fixed} cotisations + {sp_fixed} scolarités corrigées."
            ))
