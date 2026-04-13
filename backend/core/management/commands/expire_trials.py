import logging
from datetime import date

from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context

logger = logging.getLogger("core")


class Command(BaseCommand):
    help = "Expire les trials et abonnements dont la date de fin est depassee."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Affiche ce qui serait modifie sans rien toucher.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        today = date.today()

        with schema_context("public"):
            from core.models import Subscription

            # 1. Trials expires
            trials = Subscription.objects.filter(
                status="trial",
                trial_end__lt=today,
            ).select_related("mosque", "plan")

            trial_count = trials.count()
            if trial_count:
                self.stdout.write(f"[expire_trials] {trial_count} trial(s) expires :")
                for sub in trials:
                    self.stdout.write(
                        f"  - {sub.mosque.name} (plan={sub.plan.name}, "
                        f"trial_end={sub.trial_end})"
                    )
                    if not dry_run:
                        sub.status = "expired"
                        sub.save(update_fields=["status", "updated_at"])
                        logger.info(
                            "SUBSCRIPTION EXPIRED (trial): mosque=%s plan=%s",
                            sub.mosque.name, sub.plan.name,
                        )
            else:
                self.stdout.write("[expire_trials] Aucun trial expire.")

            # 2. Abonnements actifs expires (fin de periode)
            actifs = Subscription.objects.filter(
                status="active",
                current_period_end__lt=today,
            ).select_related("mosque", "plan")

            actif_count = actifs.count()
            if actif_count:
                self.stdout.write(
                    f"[expire_trials] {actif_count} abonnement(s) actif(s) expires :"
                )
                for sub in actifs:
                    self.stdout.write(
                        f"  - {sub.mosque.name} (plan={sub.plan.name}, "
                        f"period_end={sub.current_period_end})"
                    )
                    if not dry_run:
                        sub.status = "expired"
                        sub.save(update_fields=["status", "updated_at"])
                        logger.info(
                            "SUBSCRIPTION EXPIRED (active): mosque=%s plan=%s",
                            sub.mosque.name, sub.plan.name,
                        )
            else:
                self.stdout.write("[expire_trials] Aucun abonnement actif expire.")

            # 3. Rappels J-7 et J-1
            for days_left, label in [(7, "J-7"), (1, "J-1")]:
                from datetime import timedelta
                remind_date = today + timedelta(days=days_left)

                reminders = Subscription.objects.filter(
                    status="trial",
                    trial_end=remind_date,
                ).select_related("mosque", "plan")

                for sub in reminders:
                    logger.warning(
                        "TRIAL REMINDER %s: mosque=%s plan=%s trial_end=%s",
                        label, sub.mosque.name, sub.plan.name, sub.trial_end,
                    )
                    self.stdout.write(
                        f"[expire_trials] RAPPEL {label}: {sub.mosque.name} "
                        f"— trial expire le {sub.trial_end}"
                    )

        if dry_run:
            self.stdout.write(self.style.WARNING("[expire_trials] DRY RUN — rien modifie."))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"[expire_trials] Termine : {trial_count} trial(s) + {actif_count} actif(s) expires."
            ))
