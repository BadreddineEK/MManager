"""Serializers membership -- Adherents, Annees, Paiements."""
from rest_framework import serializers

from .models import Member, MembershipPayment, MembershipYear


class MembershipYearSerializer(serializers.ModelSerializer):
    paid_count = serializers.SerializerMethodField()
    total_collected = serializers.SerializerMethodField()

    class Meta:
        model = MembershipYear
        fields = ["id", "year", "amount_expected", "is_active", "paid_count", "total_collected"]

    def get_paid_count(self, obj) -> int:
        return obj.payments.values("member_id").distinct().count()

    def get_total_collected(self, obj) -> float:
        total = sum(p.amount for p in obj.payments.all())
        return float(total)


class MemberSerializer(serializers.ModelSerializer):
    is_current_year_paid = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = [
            "id", "full_name", "email", "phone", "address",
            "created_at", "is_current_year_paid", "total_paid",
        ]
        read_only_fields = ["created_at"]

    def get_is_current_year_paid(self, obj) -> bool:
        active_year = MembershipYear.objects.filter(
            mosque=obj.mosque, is_active=True
        ).first()
        if not active_year:
            return False
        return obj.payments.filter(membership_year=active_year).exists()

    def get_total_paid(self, obj) -> float:
        total = sum(p.amount for p in obj.payments.all())
        return float(total)


class MembershipPaymentSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source="member.full_name", read_only=True)
    year_label = serializers.IntegerField(source="membership_year.year", read_only=True)

    class Meta:
        model = MembershipPayment
        fields = [
            "id", "membership_year", "year_label",
            "member", "member_name",
            "date", "amount", "method", "note", "status", "created_at",
        ]
        read_only_fields = ["created_at"]
