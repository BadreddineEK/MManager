"""Enregistrement des modèles core dans l'interface Django Admin."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import AuditLog, BankAccount, DispatchRule, Mosque, MosqueSettings, Staff, User


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


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    """Administration du personnel (imams, enseignants, entretien…)."""
    list_display = ("full_name", "role", "monthly_salary", "is_active", "mosque")
    list_filter = ("mosque", "role", "is_active")
    search_fields = ("full_name", "name_keyword", "iban_fragment")
    ordering = ("role", "full_name")


# ─────────────────────────────────────────────────────────────────────────────
# Plans & Abonnements (super-admin Nidham)
# ─────────────────────────────────────────────────────────────────────────────
from .models import Plan, Subscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        "name", "display_name", "price_monthly", "price_yearly",
        "max_families_display", "max_users_display", "max_sms_month",
        "is_active", "is_public", "sort_order",
    )
    list_filter = ("is_active", "is_public")
    search_fields = ("name", "display_name")
    ordering = ("sort_order", "price_monthly")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Identite", {"fields": ("name", "display_name", "description", "sort_order", "is_active", "is_public")}),
        ("Tarifs", {"fields": ("price_monthly", "price_yearly")}),
        ("Limites (-1 = illimite)", {"fields": ("max_families", "max_users", "max_sms_month")}),
        ("Modules", {"fields": ("modules",)}),
        ("Metadonnees", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Max familles")
    def max_families_display(self, obj):
        return "Illimite" if obj.max_families == -1 else obj.max_families

    @admin.display(description="Max users")
    def max_users_display(self, obj):
        return "Illimite" if obj.max_users == -1 else obj.max_users


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("mosque", "plan", "status", "billing_cycle", "trial_end", "current_period_end", "sms_used_this_month", "created_at")
    list_filter = ("plan", "status", "billing_cycle")
    search_fields = ("mosque__name", "mosque__slug")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "sms_used_this_month", "sms_reset_date")
    raw_id_fields = ("mosque",)
    fieldsets = (
        ("Mosquee & Plan", {"fields": ("mosque", "plan", "status", "billing_cycle")}),
        ("Periode", {"fields": ("trial_end", "current_period_start", "current_period_end")}),
        ("Paiement", {"fields": ("stripe_customer_id", "stripe_subscription_id", "helloasso_subscription_id"), "classes": ("collapse",)}),
        ("SMS", {"fields": ("sms_used_this_month", "sms_reset_date")}),
        ("Metadonnees", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
    actions = ["action_activate", "action_suspend", "action_upgrade_pro"]

    @admin.action(description="Activer")
    def action_activate(self, request, queryset):
        n = queryset.update(status="active")
        self.message_user(request, f"{n} abonnement(s) active(s).")

    @admin.action(description="Suspendre (expired)")
    def action_suspend(self, request, queryset):
        n = queryset.update(status="expired")
        self.message_user(request, f"{n} abonnement(s) suspendu(s).")

    @admin.action(description="Upgrader vers Pro")
    def action_upgrade_pro(self, request, queryset):
        try:
            pro = Plan.objects.get(name="pro")
        except Plan.DoesNotExist:
            self.message_user(request, "Plan pro introuvable.", level="error")
            return
        n = queryset.update(plan=pro, status="active")
        self.message_user(request, f"{n} abonnement(s) upgrades vers Pro.")
