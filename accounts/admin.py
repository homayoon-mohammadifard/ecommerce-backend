from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.forms import CustomUserChangeForm, CustomUserCreationForm
from accounts.models import PhoneOTP, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    ordering = ("phone_number",)
    list_display = (
        "phone_number",
        "first_name",
        "last_name",
        "email",
        "role",
        "is_staff",
        "is_active",
        "phone_verified",
    )
    list_filter = ("role", "is_staff", "is_active", "is_superuser")
    search_fields = ("phone_number", "first_name", "last_name", "email")
    filter_horizontal = ("groups", "user_permissions")

    fieldsets = (
        (None, {"fields": ("phone_number", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email", "role")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "phone_verified",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "phone_number",
                    "password1",
                    "password2",
                    "email",
                    "first_name",
                    "last_name",
                    "role",
                    "is_staff",
                    "is_superuser",
                    "is_active",
                ),
            },
        ),
    )
    readonly_fields = ("last_login", "created_at", "updated_at")


@admin.register(PhoneOTP)
class PhoneOTPAdmin(admin.ModelAdmin):
    list_display = (
        "phone_number",
        "purpose",
        "created_at",
        "expires_at",
        "consumed_at",
        "superseded_at",
        "attempt_count",
    )
    list_filter = ("purpose",)
    search_fields = ("phone_number",)
    ordering = ("-created_at",)
    readonly_fields = (
        "phone_number",
        "purpose",
        "code_hmac",
        "payload",
        "created_at",
        "expires_at",
        "consumed_at",
        "superseded_at",
        "attempt_count",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
