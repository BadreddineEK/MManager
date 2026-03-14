from django.contrib import admin

from .models import TreasuryTransaction


@admin.register(TreasuryTransaction)
class TreasuryTransactionAdmin(admin.ModelAdmin):
    list_display = ("date", "label", "direction", "category", "amount", "method", "mosque")
    list_filter = ("mosque", "direction", "category", "method")
    search_fields = ("label", "note")
    ordering = ("-date",)
    date_hierarchy = "date"
