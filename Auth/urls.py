from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    RegisterView,
    LoginView,
    LogoutView,
    ProfileView,
    ChangePasswordView,
    ForgotPasswordView,
    ResetPasswordView,
    GoogleOAuthView,
    CreateAdminView,
    VerifyEmailView,
    ResendVerificationCodeView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("profile/", ProfileView.as_view(), name="auth-profile"),
    path("profile/change-password/", ChangePasswordView.as_view(), name="auth-change-password"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="auth-forgot-password"),
    path("reset-password/", ResetPasswordView.as_view(), name="auth-reset-password"),
    path("google/", GoogleOAuthView.as_view(), name="auth-google"),
    path("admin/create/", CreateAdminView.as_view(), name="auth-create-admin"),
    path("verify-email/", VerifyEmailView.as_view(), name="auth-verify-email"),
    path("resend-verification/", ResendVerificationCodeView.as_view(), name="auth-resend-verification"),
]