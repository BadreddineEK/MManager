"""Enregistrement des modèles core dans l'interface Django Admin."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import AuditLog, BankAccount, DispatchRule, Mosque, MosqueSettings, User


@admin.register(Mosque)
class MosqueAdmin(admin.ModelAdmin):
    """Administration des mosquées."""

    list_display = ("name", "slug", "timezone", "created_at")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)


@admin.register(MosqueSettings)
class MosqueSettingsAdmin(admin.ModelAdmin):
    """Administration des paramètres mosquée."""

    list_display = (
        "mosque",
        "active_school_year_label",
        "school_fee_default",
        "school_fee_mode",
        "membership_fee_amount",
        "membership_fee_mode",
    )
    search_fields = ("mosque__name",)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Administration des utilisateurs Mosquée Manager."""

    list_display = ("email", "username", "mosque", "role", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_active", "is_superuser", "role", "mosque")
    search_fields = ("email", "username", "first_name", "last_name")
    ordering = ("-date_joined",)

    # Ajouter les champs mosque + role dans les formulaires d'édition
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Mosquée Manager",
            {
                "fields": ("mosque", "role"),
            },
        ),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            "Mosquée Manager",
            {
                "fields": ("mosque", "role"),
            },
        ),
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Administration des logs d'audit — lecture seule."""

    list_display = ("created_at", "mosque", "user", "action", "entity", "entity_id")
    list_filter = ("mosque", "action", "entity")
    search_fields = ("action", "entity", "user__email")
    ordering = ("-created_at",)
    readonly_fields = ("mosque", "user", "action", "entity", "entity_id", "payload", "created_at")

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ("mosque", "label", "bank_name", "account_number", "regime", "is_active")
    list_filter = ("mosque", "regime", "is_active")
    search_fields = ("label", "account_number", "bank_name")
    ordering = ("mosque", "regime", "label")


@admin.register(DispatchRule)
class DispatchRuleAdmin(admin.ModelAdmin):
    list_display = ("mosque", "priority", "keyword", "field", "category", "direction", "is_active")
    list_filter = ("mosque", "category", "direction", "field", "is_active")
    search_fields = ("keyword",)
    ordering = ("mosque", "priority", "keyword")
