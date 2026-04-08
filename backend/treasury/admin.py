from django.contrib import admin

from .models import Campaign, CashCount, CashDenomination, TreasuryTransaction


class CashDenominationInline(admin.TabularInline):
    model = CashDenomination
    extra = 0


@admin.register(CashCount)
class CashCountAdmin(admin.ModelAdmin):
    list_display = ("date", "mosque", "created_by", "created_at")
    list_filter = ("mosque",)
    search_fields = ("note", "created_by")
    ordering = ("-date",)
    inlines = [CashDenominationInline]



@admin.register(TreasuryTransaction)
class TreasuryTransactionAdmin(admin.ModelAdmin):
    list_display = ("date", "label", "direction", "category", "amount", "method", "regime_fiscal", "campaign", "mosque")
    list_filter = ("mosque", "direction", "category", "method", "regime_fiscal", "campaign")
    search_fields = ("label", "note")
    ordering = ("-date",)
    date_hierarchy = "date"
    autocomplete_fields = ["campaign"]


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "mosque", "icon", "goal_amount", "status", "show_on_kpi", "start_date", "end_date")
    list_filter = ("mosque", "status", "show_on_kpi")
    search_fields = ("name", "description")
    ordering = ("-created_at",)
