"""
Serializers pour BankAccount et DispatchRule.
"""
from rest_framework import serializers

from .models import BankAccount, DispatchRule


class BankAccountSerializer(serializers.ModelSerializer):
    """Serializer complet pour un compte bancaire."""

    class Meta:
        model = BankAccount
        fields = [
            "id",
            "label",
            "bank_name",
            "account_number",
            "regime",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class DispatchRuleSerializer(serializers.ModelSerializer):
    """Serializer complet pour une règle de dispatch."""

    class Meta:
        model = DispatchRule
        fields = [
            "id",
            "keyword",
            "field",
            "category",
            "direction",
            "priority",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
