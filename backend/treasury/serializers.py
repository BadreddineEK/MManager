"""
Serializers Tresorerie
"""
from rest_framework import serializers

from .models import TreasuryTransaction


class TreasuryTransactionSerializer(serializers.ModelSerializer):
    direction_display = serializers.CharField(source="get_direction_display", read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    method_display = serializers.CharField(source="get_method_display", read_only=True)

    class Meta:
        model = TreasuryTransaction
        fields = [
            "id",
            "date",
            "category",
            "category_display",
            "label",
            "direction",
            "direction_display",
            "amount",
            "method",
            "method_display",
            "note",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "direction_display", "category_display", "method_display"]
