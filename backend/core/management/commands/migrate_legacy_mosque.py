"""
Commande de migration : migrate_legacy_mosque
==============================================
Migre les données d'une mosquée depuis l'ANCIEN système (mono-schema, main branch)
vers le NOUVEAU système multi-tenant (feature/multi-tenant-saas).

Usage :
    python manage.py migrate_legacy_mosque --list
    python manage.py migrate_legacy_mosque --mosque-slug meximieux --dry-run
    python manage.py migrate_legacy_mosque --mosque-slug meximieux
    python manage.py migrate_legacy_mosque --mosque-slug meximieux \
        --tenant-schema mosquee_meximieux \
        --tenant-domain mosquee-meximieux.nidham.local \
        --admin-password MonMotDePasse123!
"""
import logging
from decimal import Decimal
from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

logger = logging.getLogger(__name__)
User = get_user_model()


def _table_exists(table_name: str) -> bool:
    with connection.cursor() as cur:
        cur.execute(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s)",
            [table_name],
        )
        return cur.fetchone()[0]


def _legacy_mosque_list() -> list[dict]:
    if not _table_exists("core_mosque"):
        return []
    with connection.cursor() as cur:
        cur.execute(
            "SELECT id, name, slug, timezone, created_at FROM public.core_mosque ORDER BY id"
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def _legacy_fetch(table: str, mosque_id: int) -> list[dict]:
    if not _table_exists(table):
        return []
    with connection.cursor() as cur:
        cur.execute(
            f"SELECT * FROM public.{table} WHERE mosque_id = %s", [mosque_id]
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def _fetch_cashdenoms(cc_ids: list[int]) -> dict[int, list[dict]]:
    if not cc_ids or not _table_exists("treasury_cashdenomination"):
        return {}
    with connection.cursor() as cur:
        cur.execute(
            "SELECT * FROM public.treasury_cashdenomination WHERE cash_count_id = ANY(%s)",
            [cc_ids],
        )
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    result: dict[int, list[dict]] = {}
    for row in rows:
        result.setdefault(row["cash_count_id"], []).append(row)
    return result


class Command(BaseCommand):
    help = "Migre une mosquée de l'ancien système vers le nouveau multi-tenant"

    def add_arguments(self, parser):
        parser.add_argument("--list", action="store_true",
                            help="Liste les mosquées disponibles dans les anciennes tables")
        parser.add_argument("--mosque-slug", type=str,
                            help="Slug de la mosquée à migrer")
        parser.add_argument("--tenant-schema", type=str, default=None,
                            help="Nom du schema PostgreSQL (défaut: mosquee_<slug>)")
        parser.add_argument("--tenant-domain", type=str, default=None,
                            help="Domaine du tenant (défaut: mosquee-<slug>.nidham.local)")
        parser.add_argument("--admin-username", type=str, default=None,
                            help="Username admin (défaut: <schema>__admin)")
        parser.add_argument("--admin-password", type=str, default="ChangeMoi123!",
                            help="Mot de passe admin (défaut: ChangeMoi123!)")
        parser.add_argument("--dry-run", action="store_true",
                            help="Simule la migration sans écrire en base")

    def handle(self, *args: Any, **options: Any) -> None:
        if options["list"]:
            self._list_mosques()
            return
        if not options["mosque_slug"]:
            raise CommandError(
                "Fournir --mosque-slug ou --list.\n"
                "Exemple : python manage.py migrate_legacy_mosque --mosque-slug meximieux"
            )
        self._migrate(options)

    # ── Liste ──────────────────────────────────────────────────────────────────

    def _list_mosques(self) -> None:
        mosques = _legacy_mosque_list()
        if not mosques:
            self.stdout.write(self.style.WARNING(
                "Aucune table 'core_mosque' (ancien système) trouvée dans le schéma public.\n"
                "Les données ont peut-être été supprimées (docker compose down -v)."
            ))
            return
        self.stdout.write(self.style.SUCCESS(f"\n{len(mosques)} mosquée(s) dans l'ancien système :\n"))
        for m in mosques:
            n_members  = len(_legacy_fetch("membership_member", m["id"]))
            n_families = len(_legacy_fetch("school_family", m["id"]))
            n_children = len(_legacy_fetch("school_child", m["id"]))
            n_tx       = len(_legacy_fetch("treasury_transaction", m["id"]))
            self.stdout.write(
                f"  id={m['id']}  slug={m['slug']!r}  name={m['name']!r}\n"
                f"    -> {n_members} membres, {n_families} familles, "
                f"{n_children} enfants, {n_tx} transactions\n"
            )

    # ── Migration ──────────────────────────────────────────────────────────────

    def _migrate(self, options: dict) -> None:
        from django_tenants.utils import schema_context
        from core.models import Domain, Mosque

        slug    = options["mosque_slug"]
        dry_run = options["dry_run"]

        # 1. Trouver la mosquée legacy
        mosques = _legacy_mosque_list()
        if not mosques:
            raise CommandError(
                "Table 'core_mosque' introuvable dans le schéma public.\n"
                "Les anciennes données n'existent plus dans cette base de données.\n"
                "Utilise l'API ou l'admin pour créer manuellement la mosquée."
            )
        legacy = next((m for m in mosques if m["slug"] == slug), None)
        if legacy is None:
            available = ", ".join(m["slug"] for m in mosques)
            raise CommandError(f"Slug '{slug}' introuvable. Disponibles : {available}")

        mosque_id     = legacy["id"]
        schema_name   = options["tenant_schema"] or f"mosquee_{slug.replace('-', '_')}"
        domain_name   = options["tenant_domain"] or f"mosquee-{slug}.nidham.local"
        admin_username = options["admin_username"] or f"{schema_name}__admin"
        admin_password = options["admin_password"]

        prefix = "[DRY-RUN] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"\n{prefix}Migration : {legacy['name']!r} (id={mosque_id})\n"
            f"  schema : {schema_name}\n"
            f"  domain : {domain_name}\n"
            f"  admin  : {admin_username}\n"
        ))

        # 2. Charger toutes les données legacy
        legacy_settings    = self._fetch_settings(mosque_id)
        legacy_sy          = _legacy_fetch("school_year", mosque_id)
        legacy_my          = _legacy_fetch("membership_year", mosque_id)
        legacy_families    = _legacy_fetch("school_family", mosque_id)
        legacy_children    = _legacy_fetch("school_child", mosque_id)
        legacy_school_pmts = _legacy_fetch("school_payment", mosque_id)
        legacy_members     = _legacy_fetch("membership_member", mosque_id)
        legacy_memb_pmts   = _legacy_fetch("membership_payment", mosque_id)
        legacy_tx          = _legacy_fetch("treasury_transaction", mosque_id)
        legacy_campaigns   = _legacy_fetch("treasury_campaign", mosque_id)
        legacy_cashcounts  = _legacy_fetch("treasury_cashcount", mosque_id)
        cashdenoms         = _fetch_cashdenoms([cc["id"] for cc in legacy_cashcounts])

        self.stdout.write("  Donnees a migrer :")
        self.stdout.write(f"    {len(legacy_sy)} annees scolaires")
        self.stdout.write(f"    {len(legacy_my)} annees cotisation")
        self.stdout.write(f"    {len(legacy_families)} familles")
        self.stdout.write(f"    {len(legacy_children)} enfants")
        self.stdout.write(f"    {len(legacy_school_pmts)} paiements ecole")
        self.stdout.write(f"    {len(legacy_members)} membres")
        self.stdout.write(f"    {len(legacy_memb_pmts)} paiements cotisation")
        self.stdout.write(f"    {len(legacy_tx)} transactions tresorerie")
        self.stdout.write(f"    {len(legacy_campaigns)} campagnes")
        self.stdout.write(f"    {len(legacy_cashcounts)} pointages caisse")

        if dry_run:
            self.stdout.write(self.style.WARNING("\n[DRY-RUN] Aucune ecriture effectuee."))
            return

        # 3. Créer le tenant (en dehors de schema_context)
        if Mosque.objects.filter(schema_name=schema_name).exists():
            raise CommandError(
                f"Le tenant '{schema_name}' existe deja. "
                "Supprime-le d'abord ou utilise --tenant-schema avec un autre nom."
            )

        self.stdout.write("\n  [1/9] Creation du tenant...")
        with transaction.atomic():
            mosque_obj = Mosque.objects.create(
                schema_name=schema_name,
                name=legacy["name"],
                slug=slug,
                timezone=legacy.get("timezone", "Europe/Paris"),
            )
            Domain.objects.create(
                domain=domain_name,
                tenant=mosque_obj,
                is_primary=True,
            )
        self.stdout.write(self.style.SUCCESS(
            f"    OK Tenant '{schema_name}' cree (id={mosque_obj.id})"
        ))

        # 4. Tout dans le schema du nouveau tenant
        with schema_context(schema_name):
            self._create_settings(mosque_obj, legacy_settings)
            sy_map  = self._create_school_years(legacy_sy, mosque_obj)
            my_map  = self._create_membership_years(legacy_my, mosque_obj)
            fam_map = self._create_families(legacy_families, mosque_obj)
            ch_map  = self._create_children(legacy_children, mosque_obj, fam_map)
            self._create_school_payments(legacy_school_pmts, mosque_obj, sy_map, fam_map, ch_map)
            mb_map  = self._create_members(legacy_members, mosque_obj)
            self._create_membership_payments(legacy_memb_pmts, mosque_obj, my_map, mb_map)
            camp_map = self._create_campaigns(legacy_campaigns, mosque_obj)
            self._create_transactions(legacy_tx, mosque_obj, camp_map, fam_map, mb_map, sy_map, my_map)
            self._create_cashcounts(legacy_cashcounts, cashdenoms, mosque_obj)
            self._create_admin_user(mosque_obj, admin_username, admin_password)

        self.stdout.write(self.style.SUCCESS(
            f"\nMigration terminee !\n"
            f"  Tenant : {schema_name}\n"
            f"  Domain : {domain_name}\n"
            f"  Admin  : {admin_username} / {admin_password}\n"
            f"\n  Ajouter dans /etc/hosts du Pi :\n"
            f"    127.0.0.1  {domain_name}\n"
            f"\n  URL : http://{domain_name}:8100\n"
        ))

    # ── Helpers fetch ──────────────────────────────────────────────────────────

    def _fetch_settings(self, mosque_id: int) -> dict | None:
        if not _table_exists("core_mosquesettings"):
            return None
        with connection.cursor() as cur:
            cur.execute(
                "SELECT * FROM public.core_mosquesettings WHERE mosque_id = %s", [mosque_id]
            )
            row = cur.fetchone()
            if not row:
                return None
            return dict(zip([d[0] for d in cur.description], row))

    # ── Helpers création ───────────────────────────────────────────────────────

    def _create_settings(self, mosque_obj, legacy: dict | None) -> None:
        from core.models import MosqueSettings
        self.stdout.write("  [2/9] Parametres mosquee...")
        try:
            settings = mosque_obj.settings
        except Exception:
            settings = MosqueSettings(mosque=mosque_obj)
        if legacy:
            for field in ("school_levels", "school_fee_mode", "membership_fee_mode"):
                if legacy.get(field):
                    setattr(settings, field, legacy[field])
            for field in ("school_fee_default", "membership_fee_amount"):
                if legacy.get(field):
                    setattr(settings, field, Decimal(str(legacy[field])))
        settings.save()
        self.stdout.write(self.style.SUCCESS("    OK Parametres migres"))

    def _create_school_years(self, rows: list[dict], mosque_obj) -> dict[int, object]:
        from school.models import SchoolYear
        self.stdout.write(f"  [3/9] Annees scolaires ({len(rows)})...")
        mapping: dict[int, object] = {}
        for r in rows:
            obj, _ = SchoolYear.objects.get_or_create(
                label=r["label"],
                defaults=dict(mosque=mosque_obj, start_date=r["start_date"],
                              end_date=r["end_date"], is_active=r["is_active"]),
            )
            mapping[r["id"]] = obj
        self.stdout.write(self.style.SUCCESS(f"    OK {len(mapping)} annees scolaires"))
        return mapping

    def _create_membership_years(self, rows: list[dict], mosque_obj) -> dict[int, object]:
        from membership.models import MembershipYear
        self.stdout.write(f"  [4/9] Annees cotisation ({len(rows)})...")
        mapping: dict[int, object] = {}
        for r in rows:
            obj, _ = MembershipYear.objects.get_or_create(
                year=r["year"],
                defaults=dict(mosque=mosque_obj,
                              amount_expected=Decimal(str(r["amount_expected"])),
                              is_active=r["is_active"]),
            )
            mapping[r["id"]] = obj
        self.stdout.write(self.style.SUCCESS(f"    OK {len(mapping)} annees cotisation"))
        return mapping

    def _create_families(self, rows: list[dict], mosque_obj) -> dict[int, object]:
        from school.models import Family
        self.stdout.write(f"  [5/9] Familles ({len(rows)})...")
        mapping: dict[int, object] = {}
        for r in rows:
            obj, _ = Family.objects.get_or_create(
                primary_contact_name=r["primary_contact_name"],
                email=r.get("email", ""),
                defaults=dict(mosque=mosque_obj, phone1=r.get("phone1", ""),
                              phone2=r.get("phone2", ""), address=r.get("address", "")),
            )
            mapping[r["id"]] = obj
        self.stdout.write(self.style.SUCCESS(f"    OK {len(mapping)} familles"))
        return mapping

    def _create_children(self, rows: list[dict], mosque_obj, family_map: dict) -> dict[int, object]:
        from school.models import Child
        self.stdout.write(f"  [5/9] Enfants ({len(rows)})...")
        mapping: dict[int, object] = {}
        skipped = 0
        for r in rows:
            fam = family_map.get(r["family_id"])
            if not fam:
                skipped += 1
                continue
            obj, _ = Child.objects.get_or_create(
                family=fam, first_name=r["first_name"],
                defaults=dict(mosque=mosque_obj, birth_date=r.get("birth_date"),
                              level=r.get("level", "")),
            )
            mapping[r["id"]] = obj
        self.stdout.write(self.style.SUCCESS(
            f"    OK {len(mapping)} enfants" + (f" ({skipped} ignores)" if skipped else "")
        ))
        return mapping

    def _create_school_payments(self, rows, mosque_obj, sy_map, fam_map, ch_map):
        from school.models import SchoolPayment
        self.stdout.write(f"  [5/9] Paiements ecole ({len(rows)})...")
        created = 0
        for r in rows:
            sy, fam = sy_map.get(r["school_year_id"]), fam_map.get(r["family_id"])
            if not sy or not fam:
                continue
            child = ch_map.get(r.get("child_id")) if r.get("child_id") else None
            _, was = SchoolPayment.objects.get_or_create(
                school_year=sy, family=fam, date=r["date"],
                amount=Decimal(str(r["amount"])),
                defaults=dict(mosque=mosque_obj, child=child,
                              method=r.get("method", "cash"), note=r.get("note", "")),
            )
            if was:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"    OK {created} paiements ecole"))

    def _create_members(self, rows: list[dict], mosque_obj) -> dict[int, object]:
        from membership.models import Member
        self.stdout.write(f"  [6/9] Membres ({len(rows)})...")
        mapping: dict[int, object] = {}
        for r in rows:
            obj, _ = Member.objects.get_or_create(
                full_name=r["full_name"],
                defaults=dict(mosque=mosque_obj, email=r.get("email", ""),
                              phone=r.get("phone", ""), address=r.get("address", "")),
            )
            mapping[r["id"]] = obj
        self.stdout.write(self.style.SUCCESS(f"    OK {len(mapping)} membres"))
        return mapping

    def _create_membership_payments(self, rows, mosque_obj, my_map, mb_map):
        from membership.models import MembershipPayment
        self.stdout.write(f"  [7/9] Paiements cotisations ({len(rows)})...")
        created = 0
        for r in rows:
            my, mb = my_map.get(r["membership_year_id"]), mb_map.get(r["member_id"])
            if not my or not mb:
                continue
            _, was = MembershipPayment.objects.get_or_create(
                membership_year=my, member=mb, date=r["date"],
                amount=Decimal(str(r["amount"])),
                defaults=dict(mosque=mosque_obj,
                              method=r.get("method", "cash"), note=r.get("note", "")),
            )
            if was:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"    OK {created} paiements cotisations"))

    def _create_campaigns(self, rows: list[dict], mosque_obj) -> dict[int, object]:
        from treasury.models import Campaign
        self.stdout.write(f"  [8/9] Campagnes ({len(rows)})...")
        mapping: dict[int, object] = {}
        for r in rows:
            obj, _ = Campaign.objects.get_or_create(
                name=r["name"],
                defaults=dict(
                    mosque=mosque_obj,
                    description=r.get("description", ""),
                    icon=r.get("icon", "🎯"),
                    goal_amount=Decimal(str(r["goal_amount"])) if r.get("goal_amount") else None,
                    start_date=r.get("start_date"),
                    end_date=r.get("end_date"),
                    status=r.get("status", "active"),
                    show_on_kpi=r.get("show_on_kpi", True),
                ),
            )
            mapping[r["id"]] = obj
        self.stdout.write(self.style.SUCCESS(f"    OK {len(mapping)} campagnes"))
        return mapping

    def _create_transactions(self, rows, mosque_obj, camp_map, fam_map, mb_map, sy_map, my_map):
        from treasury.models import TreasuryTransaction
        self.stdout.write(f"  [8/9] Transactions ({len(rows)})...")
        created = 0
        for r in rows:
            _, was = TreasuryTransaction.objects.get_or_create(
                date=r["date"], label=r["label"],
                amount=Decimal(str(r["amount"])), direction=r["direction"],
                defaults=dict(
                    mosque=mosque_obj,
                    category=r.get("category", "autre"),
                    method=r.get("method", "cash"),
                    note=r.get("note", ""),
                    regime_fiscal=r.get("regime_fiscal", ""),
                    source=r.get("source", "manual"),
                    import_operation_id=r.get("import_operation_id"),
                    import_status=r.get("import_status"),
                    campaign=camp_map.get(r["campaign_id"]) if r.get("campaign_id") else None,
                    family=fam_map.get(r["family_id"]) if r.get("family_id") else None,
                    school_year=sy_map.get(r["school_year_id"]) if r.get("school_year_id") else None,
                    member=mb_map.get(r["member_id"]) if r.get("member_id") else None,
                    membership_year=my_map.get(r["membership_year_id"]) if r.get("membership_year_id") else None,
                ),
            )
            if was:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"    OK {created} transactions"))

    def _create_cashcounts(self, cashcounts: list[dict], cashdenoms: dict, mosque_obj) -> None:
        from treasury.models import CashCount, CashDenomination
        self.stdout.write(f"  [8/9] Pointages caisse ({len(cashcounts)})...")
        for cc in cashcounts:
            obj, _ = CashCount.objects.get_or_create(
                date=cc["date"],
                defaults=dict(mosque=mosque_obj,
                              note=cc.get("note", ""),
                              created_by=cc.get("created_by", "")),
            )
            for d in cashdenoms.get(cc["id"], []):
                CashDenomination.objects.get_or_create(
                    cash_count=obj,
                    denomination=Decimal(str(d["denomination"])),
                    defaults={"quantity": d["quantity"]},
                )
        self.stdout.write(self.style.SUCCESS(f"    OK {len(cashcounts)} pointages"))

    def _create_admin_user(self, mosque_obj, username: str, password: str) -> None:
        self.stdout.write(f"  [9/9] Utilisateur admin ({username})...")
        schema = mosque_obj.schema_name
        prefixed = username if username.startswith(schema) else f"{schema}__{username}"
        if User.objects.filter(username=prefixed).exists():
            self.stdout.write(f"    -> '{prefixed}' existe deja, ignore.")
            return
        User.objects.create_superuser(
            username=prefixed,
            password=password,
            email=f"admin@{mosque_obj.slug}.nidham.local",
            mosque=mosque_obj,
            role="ADMIN",
        )
        self.stdout.write(self.style.SUCCESS(f"    OK Admin cree : {prefixed}"))
