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
    regime_fiscal_display = serializers.CharField(source="get_regime_fiscal_display", read_only=True)
    campaign_name = serializers.CharField(source="campaign.name", read_only=True, allow_null=True)
    # Liens ressources humaines (lecture seule)
    family_name = serializers.CharField(source="family.primary_contact_name", read_only=True, allow_null=True)
    member_name = serializers.CharField(source="member.full_name", read_only=True, allow_null=True)
    school_year_label = serializers.CharField(source="school_year.label", read_only=True, allow_null=True)
    membership_year_label = serializers.IntegerField(source="membership_year.year", read_only=True, allow_null=True)
    # Compte bancaire
    bank_account_label = serializers.CharField(source="bank_account.label", read_only=True, allow_null=True)
    bank_account_regime = serializers.CharField(source="bank_account.regime", read_only=True, allow_null=True)
    import_status_display = serializers.CharField(source="get_import_status_display", read_only=True)

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
            "regime_fiscal",
            "regime_fiscal_display",
            "campaign",
            "campaign_name",
            "family",
            "family_name",
            "school_year",
            "school_year_label",
            "member",
            "member_name",
            "membership_year",
            "membership_year_label",
            # Import bancaire
            "bank_account",
            "bank_account_label",
            "bank_account_regime",
            "source",
            "import_operation_id",
            "import_status",
            "import_status_display",
            "created_at",
        ]
        read_only_fields = [
            "id", "created_at",
            "direction_display", "category_display", "method_display",
            "regime_fiscal_display", "campaign_name",
            "family_name", "member_name", "school_year_label", "membership_year_label",
            "bank_account_label", "bank_account_regime", "import_status_display",
        ]
