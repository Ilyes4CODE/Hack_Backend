from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, PasswordResetToken


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User

    list_display = (
        "email",
        "role",
        "is_staff",
        "is_active",
        "is_email_verified",
        "created_at",
    )

    list_filter = (
        "role",
        "is_staff",
        "is_active",
        "is_email_verified",
        "created_at",
    )

    search_fields = (
        "email",
        "first_name",
        "last_name",
        "phone",
    )

    ordering = ("-created_at",)

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        ("Authentication", {
            "fields": ("email", "password", "google_id")
        }),
        ("Personal Info", {
            "fields": (
                "first_name",
                "last_name",
                "phone",
                "bio",
                "avatar",
            )
        }),
        ("Permissions", {
            "fields": (
                "role",
                "is_active",
                "is_staff",
                "is_superuser",
                "is_email_verified",
                "groups",
                "user_permissions",
            )
        }),
        ("Important Dates", {
            "fields": (
                "last_login",
                "created_at",
                "updated_at",
            )
        }),
        ("UUID", {
            "fields": ("id",)
        }),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "email",
                "password1",
                "password2",
                "role",
                "is_active",
                "is_staff",
            ),
        }),
    )


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "token",
        "created_at",
        "is_used",
    )

    list_filter = (
        "is_used",
        "created_at",
    )

    search_fields = (
        "user__email",
        "token",
    )

    readonly_fields = (
        "token",
        "created_at",
    )

    ordering = ("-created_at",)