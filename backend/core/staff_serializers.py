"""Sérialiseurs pour le modèle Staff."""
from rest_framework import serializers

from .models import Staff


class StaffSerializer(serializers.ModelSerializer):
    """Sérialiseur complet du personnel."""

    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = Staff
        fields = [
            "id",
            "full_name",
            "role",
            "role_display",
            "monthly_salary",
            "iban_fragment",
            "name_keyword",
            "phone",
            "email",
            "note",
            "is_active",
            "start_date",
            "end_date",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
