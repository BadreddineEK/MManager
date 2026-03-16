"""
Serializers Tresorerie
"""
from rest_framework import serializers

from .models import Campaign, TreasuryTransaction


class CampaignSerializer(serializers.ModelSerializer):
    collected_amount = serializers.SerializerMethodField()
    progress_percent = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Campaign
        fields = [
            "id", "name", "description", "icon",
            "goal_amount", "start_date", "end_date",
            "status", "status_display", "show_on_kpi",
            "collected_amount", "progress_percent",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "collected_amount", "progress_percent", "status_display"]

    def get_collected_amount(self, obj):
        return obj.collected_amount

    def get_progress_percent(self, obj):
        return obj.progress_percent


class TreasuryTransactionSerializer(serializers.ModelSerializer):
    direction_display = serializers.CharField(source="get_direction_display", read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    method_display = serializers.CharField(source="get_method_display", read_only=True)
    campaign_name = serializers.CharField(source="campaign.name", read_only=True, allow_null=True)

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
            "campaign",
            "campaign_name",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "direction_display", "category_display", "method_display", "campaign_name"]
