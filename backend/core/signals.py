"""
Signaux Django — core
======================
Automatise l'initialisation d'une mosquée dès sa création :
  - MosqueSettings avec valeurs par défaut
  - SchoolYear pour l'année scolaire en cours
  - MembershipYear pour l'année civile en cours

NOTE multi-tenant : on utilise post_schema_sync (django-tenants) au lieu de post_save
car les tables tenant (school_year, membership_year) n'existent QU'APRÈS que le schéma
tenant est créé et migré. post_save se déclenche AVANT la migration du schéma.
"""
import logging
from datetime import date

from django.db.models.signals import post_save
from django.dispatch import receiver
from django_tenants.signals import post_schema_sync

logger = logging.getLogger("core")


@receiver(post_schema_sync, sender=None)
def mosque_post_schema_sync(sender, tenant, **kwargs):
    """
    Après création + migration du schéma tenant :
    1. Crée MosqueSettings avec des valeurs par défaut sensées
    2. Crée un SchoolYear pour l'année scolaire courante (ex: 2025-2026)
    3. Crée un MembershipYear pour l'année civile courante
    """
    from django.db import connection
    from core.models import MosqueSettings
    from membership.models import MembershipYear
    from school.models import SchoolYear

    # Activer le schéma tenant
    connection.set_tenant(tenant)

    today = date.today()
    year = today.year
    month = today.month

    # Année scolaire : si on est entre sept et déc → ex: "2025-2026"
    # si on est entre jan et août → ex: "2024-2025"
    if month >= 9:
        school_label = f"{year}-{year + 1}"
    else:
        school_label = f"{year - 1}-{year}"

    # 1. MosqueSettings
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
    logger.info("SIGNAL: MosqueSettings créé pour mosquée '%s'", tenant.name)

    # 2. SchoolYear
    if month >= 9:
        start_date = date(year, 9, 1)
        end_date   = date(year + 1, 8, 31)
    else:
        start_date = date(year - 1, 9, 1)
        end_date   = date(year, 8, 31)

    SchoolYear.objects.get_or_create(
        mosque=tenant,
        label=school_label,
        defaults={
            "is_active":   True,
            "start_date":  start_date,
            "end_date":    end_date,
        },
    )
    logger.info("SIGNAL: SchoolYear '%s' créé pour mosquée '%s'", school_label, tenant.name)

    # 3. MembershipYear
    MembershipYear.objects.get_or_create(
        mosque=tenant,
        year=year,
        defaults={
            "amount_expected": 0,
            "is_active": True,
        },
    )
    logger.info("SIGNAL: MembershipYear %d créé pour mosquée '%s'", year, tenant.name)
