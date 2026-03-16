"""
Serializer pour MosqueSettings -- panneau de configuration mosquee.
"""
from rest_framework import serializers

from .models import Mosque, MosqueSettings


class MosqueSerializer(serializers.ModelSerializer):
    """Serializer leger pour les infos de la mosquee."""

    class Meta:
        model = Mosque
        fields = ["id", "name", "slug", "timezone", "created_at"]
        read_only_fields = ["id", "slug", "created_at"]


class MosqueSettingsSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour MosqueSettings.
    Inclut les infos de la mosquee imbriquees (lecture seule).
    """

    mosque_name = serializers.CharField(source="mosque.name", read_only=True)
    mosque_slug = serializers.CharField(source="mosque.slug", read_only=True)
    mosque_timezone = serializers.CharField(
        source="mosque.timezone", read_only=True
    )

    class Meta:
        model = MosqueSettings
        fields = [
            "id",
            "mosque_name",
            "mosque_slug",
            "mosque_timezone",
            # Ecole
            "school_levels",
            "school_fee_default",
            "school_fee_mode",
            # Cotisations
            "membership_fee_amount",
            "membership_fee_mode",
            # Annee scolaire
            "active_school_year_label",
            # Reçus fiscaux
            "receipt_logo_url",
            "receipt_address",
            "receipt_phone",
            "receipt_legal_mention",
            # KPI widgets
            "show_kpi_school",
            "show_kpi_membership",
            "show_kpi_treasury",
            "show_kpi_campaigns",
            "kpi_refresh_secs",
        ]
        read_only_fields = ["id", "mosque_name", "mosque_slug", "mosque_timezone"]


class OnboardingSerializer(serializers.Serializer):
    """
    Serializer pour l'onboarding initial (premiere connexion admin).

    Cree ou met a jour Mosque + MosqueSettings en une seule requete.
    """

    # Mosquee
    mosque_name = serializers.CharField(max_length=200)
    mosque_timezone = serializers.CharField(max_length=50, default="Europe/Paris")

    # Ecole
    active_school_year_label = serializers.CharField(
        max_length=50, required=False, allow_blank=True, help_text='Ex: "2025-2026"'
    )
    school_levels = serializers.ListField(
        child=serializers.CharField(max_length=10),
        default=["NP", "N1", "N2", "N3", "N4", "N5", "N6"],
    )
    school_fee_default = serializers.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    school_fee_mode = serializers.ChoiceField(
        choices=["annual", "monthly"], default="annual"
    )

    # Cotisations
    membership_fee_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    membership_fee_mode = serializers.ChoiceField(
        choices=["per_person", "per_family"], default="per_person"
    )
