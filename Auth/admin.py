from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, PasswordResetToken


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "first_name", "last_name", "is_active", "is_staff", "is_email_verified", "has_google", "created_at")
    list_filter = ("is_active", "is_staff", "is_email_verified")
    search_fields = ("email", "first_name", "last_name", "phone")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at", "username", "avatar_preview")

    fieldsets = (
        ("Account", {"fields": ("id", "email", "username", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name", "phone", "bio", "avatar", "avatar_preview")}),
        ("Status", {"fields": ("is_active", "is_staff", "is_superuser", "is_email_verified")}),
        ("OAuth", {"fields": ("google_id",)}),
        ("Permissions", {"fields": ("groups", "user_permissions")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "first_name", "last_name", "password1", "password2"),
            },
        ),
    )

    def has_google(self, obj):
        return bool(obj.google_id)
    has_google.boolean = True
    has_google.short_description = "Google OAuth"

    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html('<img src="{}" width="80" height="80" style="border-radius:50%;object-fit:cover;" />', obj.avatar.url)
        return "No avatar"
    avatar_preview.short_description = "Avatar Preview"


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "token", "is_used", "created_at", "expired")
    list_filter = ("is_used",)
    search_fields = ("user__email",)
    readonly_fields = ("token", "created_at")
    ordering = ("-created_at",)

    def expired(self, obj):
        return obj.is_expired()
    expired.boolean = True
    expired.short_description = "Expired"