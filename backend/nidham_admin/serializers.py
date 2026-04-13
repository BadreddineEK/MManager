"""Serializers super-admin Nidham."""
import datetime

from django_tenants.utils import schema_context
from rest_framework import serializers

from core.models import Domain, Mosque, Plan, Subscription


class PlanSerializer(serializers.ModelSerializer):
    """CRUD complet sur les plans tarifaires."""
    subscriptions_count = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = [
            "id", "name", "price_monthly", "price_yearly",
            "max_families", "max_users", "max_sms_month",
            "modules", "is_active", "created_at", "subscriptions_count",
        ]
        read_only_fields = ["id", "created_at", "subscriptions_count"]

    def get_subscriptions_count(self, obj):
        return obj.subscriptions.count()


class SubscriptionInlineSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    plan_display = serializers.CharField(source="plan.get_name_display", read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id", "plan_name", "plan_display", "status",
            "billing_cycle", "trial_end",
            "current_period_start", "current_period_end",
            "is_active",
        ]


class MosqueAdminSerializer(serializers.ModelSerializer):
    """Vue complète d'une mosquée pour le super-admin."""
    domain = serializers.SerializerMethodField()
    subscription = SubscriptionInlineSerializer(read_only=True)
    families_count = serializers.SerializerMethodField()
    users_count = serializers.SerializerMethodField()

    class Meta:
        model = Mosque
        fields = [
            "id", "name", "slug", "schema_name", "timezone",
            "created_at", "domain", "subscription",
            "families_count", "users_count",
        ]
        read_only_fields = ["id", "schema_name", "created_at"]

    def get_domain(self, obj):
        d = Domain.objects.filter(tenant=obj, is_primary=True).first()
        return d.domain if d else None

    def get_families_count(self, obj):
        try:
            with schema_context(obj.schema_name):
                from school.models import Family
                return Family.objects.count()
        except Exception:
            return 0

    def get_users_count(self, obj):
        try:
            with schema_context(obj.schema_name):
                from core.models import User
                return User.objects.count()
        except Exception:
            return 0


class ChangePlanSerializer(serializers.Serializer):
    """Changer le plan d'une mosquée."""
    plan_id = serializers.IntegerField()
    status = serializers.ChoiceField(
        choices=["trial", "active", "expired", "cancelled"],
        default="active",
    )
    billing_cycle = serializers.ChoiceField(
        choices=["monthly", "yearly"],
        default="monthly",
    )
    trial_end = serializers.DateField(required=False, allow_null=True)
    period_end = serializers.DateField(required=False, allow_null=True)

    def validate_plan_id(self, value):
        if not Plan.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Plan introuvable.")
        return value
