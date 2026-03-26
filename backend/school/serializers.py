"""Serializers school -- Familles, Enfants, Annees scolaires, Paiements."""
from rest_framework import serializers

from .models import Child, Family, SchoolPayment, SchoolYear


class SchoolYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolYear
        fields = ["id", "label", "start_date", "end_date", "is_active"]


class ChildSerializer(serializers.ModelSerializer):
    class Meta:
        model = Child
        fields = ["id", "family", "first_name", "birth_date", "level", "created_at"]
        read_only_fields = ["created_at"]


class ChildInlineSerializer(serializers.ModelSerializer):
    """Version compacte pour afficher les enfants dans la liste des familles."""
    class Meta:
        model = Child
        fields = ["id", "first_name", "level", "birth_date"]


class FamilySerializer(serializers.ModelSerializer):
    children = ChildInlineSerializer(many=True, read_only=True)
    children_count = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()

    class Meta:
        model = Family
        fields = [
            "id",
            "primary_contact_name",
            "email",
            "phone1",
            "phone2",
            "address",
            "created_at",
            "children",
            "children_count",
            "total_paid",
        ]
        read_only_fields = ["created_at"]

    def get_children_count(self, obj) -> int:
        return obj.children.count()

    def get_total_paid(self, obj) -> float:
        total = sum(p.amount for p in obj.payments.all())
        return float(total)


class SchoolPaymentSerializer(serializers.ModelSerializer):
    family_name = serializers.CharField(source="family.primary_contact_name", read_only=True)
    child_name = serializers.CharField(source="child.first_name", read_only=True, default=None)
    school_year_label = serializers.CharField(source="school_year.label", read_only=True)
    method_display = serializers.CharField(source="get_method_display", read_only=True)

    class Meta:
        model = SchoolPayment
        fields = [
            "id",
            "school_year",
            "school_year_label",
            "family",
            "family_name",
            "child",
            "child_name",
            "date",
            "amount",
            "method",
            "method_display",
            "note",
            "created_at",
        ]
        read_only_fields = ["created_at"]
