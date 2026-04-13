"""
Signaux Django — core (multi-tenant)
=====================================
post_schema_sync: initialise les donnees apres creation du schema tenant.
"""
import logging
from datetime import date

from django.dispatch import receiver
from django_tenants.signals import post_schema_sync

logger = logging.getLogger("core")


@receiver(post_schema_sync, sender=None)
def mosque_post_schema_sync(sender, tenant, **kwargs):
    """
    Apres creation + migration du schema tenant:
    1. Cree MosqueSettings
    2. Cree SchoolYear pour l'annee scolaire courante
    3. Cree MembershipYear pour l'annee civile courante

    Guard: utilise un savepoint pour tester si les tables existent
    (TENANT_CREATION_FAKES_MIGRATIONS ou schema vide en test).
    """
    from django.db import connection, transaction
    from django.db.utils import ProgrammingError, OperationalError

    connection.set_tenant(tenant)

    # Verifier que les tables tenant existent avec un SAVEPOINT
    # pour ne pas corrompre la transaction courante
    tables_ok = False
    try:
        with transaction.atomic():
            from school.models import SchoolYear
            SchoolYear.objects.exists()
            tables_ok = True
    except (ProgrammingError, OperationalError):
        logger.warning("SIGNAL: tables tenant absentes pour '%s', init ignoree", tenant.name)
        return
    except Exception as e:
        if "does not exist" in str(e):
            logger.warning("SIGNAL: tables absentes pour '%s': %s", tenant.name, e)
            return
        raise

    if not tables_ok:
        return

    from core.models import MosqueSettings
    from membership.models import MembershipYear
    from school.models import SchoolYear

    today = date.today()
    year = today.year
    month = today.month

    if month >= 9:
        school_label = f"{year}-{year + 1}"
        start_date = date(year, 9, 1)
        end_date = date(year + 1, 8, 31)
    else:
        school_label = f"{year - 1}-{year}"
        start_date = date(year - 1, 9, 1)
        end_date = date(year, 8, 31)

    MosqueSettings.objects.get_or_create(
        mosque=tenant,
        defaults={
            "school_levels": ["NP", "N1", "N2", "N3", "N4", "N5", "N6"],
            "school_fee_default": 0,
            "school_fee_mode": "annual",
            "membership_fee_amount": 0,
            "membership_fee_mode": "per_person",
            "active_school_year_label": school_label,
        },
    )
    logger.info("SIGNAL: MosqueSettings cree pour '%s'", tenant.name)

    SchoolYear.objects.get_or_create(
        mosque=tenant,
        label=school_label,
        defaults={"is_active": True, "start_date": start_date, "end_date": end_date},
    )
    logger.info("SIGNAL: SchoolYear '%s' cree pour '%s'", school_label, tenant.name)

    MembershipYear.objects.get_or_create(
        mosque=tenant,
        year=year,
        defaults={"amount_expected": 0, "is_active": True},
    )
    logger.info("SIGNAL: MembershipYear %d cree pour '%s'", year, tenant.name)


# ─────────────────────────────────────────────────────────────────────────────
# Signal: notification expiration abonnement
# ─────────────────────────────────────────────────────────────────────────────
from django.db.models.signals import post_save
from django_tenants.utils import schema_context as _schema_context


def _connect_subscription_signal():
    from core.models import Subscription
    post_save.connect(subscription_status_changed, sender=Subscription)


def subscription_status_changed(sender, instance, created, **kwargs):
    """
    Logue (et plus tard: envoie un email) quand un abonnement passe en expired.
    Sender resolu dynamiquement pour eviter les imports circulaires.
    """
    if created:
        return
    update_fields = kwargs.get("update_fields") or []
    if "status" not in update_fields:
        return
    if instance.status == "expired":
        logger.warning(
            "SUBSCRIPTION EXPIRED SIGNAL: mosque=%s plan=%s — TODO: envoyer email",
            instance.mosque.name,
            instance.plan.name,
        )
        # TODO étape 16: envoyer email via send_mail ou Celery task
        # send_expiry_email(instance)


_connect_subscription_signal()
