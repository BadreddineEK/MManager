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
    # Champs pour l'année active (suivi paiement courant)
    current_year_paid = serializers.SerializerMethodField()
    current_year_due = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()

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
            "current_year_paid",
            "current_year_due",
            "payment_status",
        ]
        read_only_fields = ["created_at"]

    def _get_active_year(self, obj):
        """Retourne l'année scolaire active (cachée dans le contexte ou récupérée en DB)."""
        ctx = self.context
        if "active_school_year" not in ctx:
            ctx["active_school_year"] = SchoolYear.objects.filter(
                mosque=obj.mosque, is_active=True
            ).first()
        return ctx["active_school_year"]

    def _get_fee_default(self, obj):
        """Retourne le tarif école par défaut configuré pour la mosquée."""
        ctx = self.context
        if "school_fee_default" not in ctx:
            try:
                ctx["school_fee_default"] = float(obj.mosque.settings.school_fee_default or 0)
            except Exception:
                ctx["school_fee_default"] = 0.0
        return ctx["school_fee_default"]

    def get_children_count(self, obj) -> int:
        return obj.children.count()

    def get_total_paid(self, obj) -> float:
        """Total payé toutes années confondues."""
        total = sum(p.amount for p in obj.payments.all())
        return float(total)

    def get_current_year_paid(self, obj) -> float:
        """Montant payé pour l'année scolaire active."""
        year = self._get_active_year(obj)
        if not year:
            return 0.0
        total = sum(
            p.amount for p in obj.payments.all()
            if p.school_year_id == year.id
        )
        return float(total)

    def get_current_year_due(self, obj) -> float:
        """Montant dû pour l'année active = tarif × nombre d'enfants."""
        fee = self._get_fee_default(obj)
        n = obj.children.count()
        return float(fee * n) if fee and n else 0.0

    def get_payment_status(self, obj) -> str:
        """'paid' | 'partial' | 'unpaid'"""
        paid = self.get_current_year_paid(obj)
        due = self.get_current_year_due(obj)
        if due == 0:
            return "paid" if paid > 0 else "unpaid"
        if paid >= due:
            return "paid"
        if paid > 0:
            return "partial"
        return "unpaid"


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
            "status",
            "created_at",
        ]
        read_only_fields = ["created_at"]
