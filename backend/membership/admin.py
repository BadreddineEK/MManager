from django.contrib import admin

from .models import Member, MembershipPayment, MembershipYear


@admin.register(MembershipYear)
class MembershipYearAdmin(admin.ModelAdmin):
    list_display = ("year", "mosque", "amount_expected", "is_active")
    list_filter = ("mosque", "is_active")
    ordering = ("-year",)


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "phone", "mosque", "created_at")
    list_filter = ("mosque",)
    search_fields = ("full_name", "email", "phone")
    ordering = ("full_name",)


@admin.register(MembershipPayment)
class MembershipPaymentAdmin(admin.ModelAdmin):
    list_display = ("member", "membership_year", "amount", "method", "date", "mosque")
    list_filter = ("mosque", "membership_year", "method")
    search_fields = ("member__full_name",)
    ordering = ("-date",)
