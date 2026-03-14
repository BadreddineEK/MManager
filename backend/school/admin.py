"""Admin school -- Ecole coranique."""
from django.contrib import admin

from .models import Child, Family, SchoolPayment, SchoolYear


@admin.register(SchoolYear)
class SchoolYearAdmin(admin.ModelAdmin):
    list_display = ("label", "mosque", "start_date", "end_date", "is_active")
    list_filter = ("mosque", "is_active")
    search_fields = ("label",)


class ChildInline(admin.TabularInline):
    model = Child
    extra = 0
    fields = ("first_name", "level", "birth_date")


@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = ("primary_contact_name", "mosque", "phone1", "email", "created_at")
    list_filter = ("mosque",)
    search_fields = ("primary_contact_name", "phone1", "email")
    inlines = [ChildInline]


@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = ("first_name", "family", "level", "mosque", "created_at")
    list_filter = ("mosque", "level")
    search_fields = ("first_name", "family__primary_contact_name")


@admin.register(SchoolPayment)
class SchoolPaymentAdmin(admin.ModelAdmin):
    list_display = ("family", "school_year", "date", "amount", "method", "mosque")
    list_filter = ("mosque", "school_year", "method")
    search_fields = ("family__primary_contact_name",)
    ordering = ("-date",)
