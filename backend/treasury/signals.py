"""
Signaux Django - synchronisation paiements <-> tresorerie
==========================================================

Regle :
  - SchoolPayment / MembershipPayment sauvegarde
    -> cree ou met a jour la TreasuryTransaction associee
    -> status=validated car especes = direct en caisse
  - Si le paiement est supprime -> la TreasuryTransaction est supprimee aussi

Source :
  - cash_school  pour SchoolPayment
  - cash_cotis   pour MembershipPayment
  - Virements exclus : viendront de l'import CSV bancaire (source=import)
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


def _build_school_label(payment):
    child = payment.child
    family = payment.family
    year = payment.school_year.label if payment.school_year else ""
    if child:
        return f"Ecole - {child.first_name} {family.primary_contact_name} ({year})"
    return f"Ecole - {family.primary_contact_name} ({year})"


def _build_cotis_label(payment):
    member = payment.member
    year = payment.membership_year.year if payment.membership_year else ""
    return f"Cotisation {year} - {member.full_name}"


def _sync_school_payment(payment):
    """Cree ou met a jour la TreasuryTransaction pour un SchoolPayment."""
    from treasury.models import TreasuryTransaction

    # Virements bancaires : pas de creation auto (viendra de l'import CSV)
    if payment.method == "virement":
        return

    label = _build_school_label(payment)

    # Verifie si une TreasuryTx est deja liee (OneToOne reverse)
    try:
        existing = payment.treasury_tx
    except Exception:
        existing = None

    if existing is not None:
        # Mise a jour
        existing.date = payment.date
        existing.amount = payment.amount
        existing.method = payment.method
        existing.label = label
        existing.note = payment.note or ""
        existing.save(update_fields=["date", "amount", "method", "label", "note", "updated_at"])
    else:
        # Creation
        TreasuryTransaction.objects.create(
            mosque=payment.mosque,
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


def _sync_membership_payment(payment):
    """Cree ou met a jour la TreasuryTransaction pour un MembershipPayment."""
    from treasury.models import TreasuryTransaction

    if payment.method == "virement":
        return

    label = _build_cotis_label(payment)

    try:
        existing = payment.treasury_tx
    except Exception:
        existing = None

    if existing is not None:
        existing.date = payment.date
        existing.amount = payment.amount
        existing.method = payment.method
        existing.label = label
        existing.note = payment.note or ""
        existing.save(update_fields=["date", "amount", "method", "label", "note", "updated_at"])
    else:
        TreasuryTransaction.objects.create(
            mosque=payment.mosque,
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


@receiver(post_save, sender="school.SchoolPayment")
def on_school_payment_save(sender, instance, created, **kwargs):
    _sync_school_payment(instance)


@receiver(post_delete, sender="school.SchoolPayment")
def on_school_payment_delete(sender, instance, **kwargs):
    from treasury.models import TreasuryTransaction
    TreasuryTransaction.objects.filter(school_payment=instance).delete()


@receiver(post_save, sender="membership.MembershipPayment")
def on_membership_payment_save(sender, instance, created, **kwargs):
    _sync_membership_payment(instance)


@receiver(post_delete, sender="membership.MembershipPayment")
def on_membership_payment_delete(sender, instance, **kwargs):
    from treasury.models import TreasuryTransaction
    TreasuryTransaction.objects.filter(membership_payment=instance).delete()
