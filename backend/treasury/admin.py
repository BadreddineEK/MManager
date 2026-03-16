from django.contrib import admin

from .models import Campaign, TreasuryTransaction


@admin.register(TreasuryTransaction)
class TreasuryTransactionAdmin(admin.ModelAdmin):
    list_display = ("date", "label", "direction", "category", "amount", "method", "campaign", "mosque")
    list_filter = ("mosque", "direction", "category", "method", "campaign")
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
