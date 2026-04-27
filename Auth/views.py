from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from django.utils.html import strip_tags

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

import requests as http_requests

from .models import PasswordResetToken

User = get_user_model()


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Register a new user",
        operation_description="Creates a new NABAT account. Username is automatically set to the email address.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email", "password", "confirm_password"],
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, format="email", example="farmer@nabat.com"),
                "password": openapi.Schema(type=openapi.TYPE_STRING, format="password", example="StrongPass123!"),
                "confirm_password": openapi.Schema(type=openapi.TYPE_STRING, format="password", example="StrongPass123!"),
                "first_name": openapi.Schema(type=openapi.TYPE_STRING, example="Ahmed"),
                "last_name": openapi.Schema(type=openapi.TYPE_STRING, example="Benali"),
                "phone": openapi.Schema(type=openapi.TYPE_STRING, example="+213555123456"),
            },
        ),
        responses={
            201: openapi.Response(
                description="Registration successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "user": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "id": openapi.Schema(type=openapi.TYPE_STRING, format="uuid"),
                                "email": openapi.Schema(type=openapi.TYPE_STRING),
                                "first_name": openapi.Schema(type=openapi.TYPE_STRING),
                                "last_name": openapi.Schema(type=openapi.TYPE_STRING),
                            },
                        ),
                        "tokens": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "access": openapi.Schema(type=openapi.TYPE_STRING),
                                "refresh": openapi.Schema(type=openapi.TYPE_STRING),
                            },
                        ),
                    },
                ),
            ),
            400: "Validation error (email taken, password mismatch, etc.)",
        },
        tags=["Authentication"],
    )
    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        password = request.data.get("password", "")
        confirm_password = request.data.get("confirm_password", "")
        first_name = request.data.get("first_name", "")
        last_name = request.data.get("last_name", "")
        phone = request.data.get("phone", "")

        if not email or not password:
            return Response({"error": "Email and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        if password != confirm_password:
            return Response({"error": "Passwords do not match."}, status=status.HTTP_400_BAD_REQUEST)

        if len(password) < 8:
            return Response({"error": "Password must be at least 8 characters."}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            return Response({"error": "An account with this email already exists."}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
        )

        tokens = get_tokens_for_user(user)

        return Response(
            {
                "message": "Account created successfully. Welcome to NABAT!",
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                },
                "tokens": tokens,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Login with email and password",
        operation_description="Authenticates a user and returns JWT access and refresh tokens.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email", "password"],
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, format="email", example="farmer@nabat.com"),
                "password": openapi.Schema(type=openapi.TYPE_STRING, format="password", example="StrongPass123!"),
            },
        ),
        responses={
            200: openapi.Response(
                description="Login successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "user": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "id": openapi.Schema(type=openapi.TYPE_STRING, format="uuid"),
                                "email": openapi.Schema(type=openapi.TYPE_STRING),
                                "first_name": openapi.Schema(type=openapi.TYPE_STRING),
                                "last_name": openapi.Schema(type=openapi.TYPE_STRING),
                                "phone": openapi.Schema(type=openapi.TYPE_STRING),
                                "bio": openapi.Schema(type=openapi.TYPE_STRING),
                                "avatar": openapi.Schema(type=openapi.TYPE_STRING, format="uri", nullable=True),
                            },
                        ),
                        "tokens": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "access": openapi.Schema(type=openapi.TYPE_STRING, description="Short-lived JWT token. Send as: Authorization: Bearer <access>"),
                                "refresh": openapi.Schema(type=openapi.TYPE_STRING, description="Long-lived token. Use /auth/token/refresh/ to get a new access token."),
                            },
                        ),
                    },
                ),
            ),
            400: "Missing fields",
            401: "Invalid credentials",
        },
        tags=["Authentication"],
    )
    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        password = request.data.get("password", "")

        if not email or not password:
            return Response({"error": "Email and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.check_password(password):
            return Response({"error": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({"error": "This account has been deactivated."}, status=status.HTTP_401_UNAUTHORIZED)

        tokens = get_tokens_for_user(user)

        return Response(
            {
                "message": "Login successful.",
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "phone": user.phone,
                    "bio": user.bio,
                    "avatar": request.build_absolute_uri(user.avatar.url) if user.avatar else None,
                },
                "tokens": tokens,
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Logout (blacklist refresh token)",
        operation_description="Blacklists the provided refresh token, effectively logging the user out. The access token will still be valid until it expires — frontend must discard it.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["refresh"],
            properties={
                "refresh": openapi.Schema(type=openapi.TYPE_STRING, description="The refresh token received at login."),
            },
        ),
        responses={
            200: openapi.Response(description="Logged out successfully"),
            400: "Invalid or missing refresh token",
        },
        security=[{"Bearer": []}],
        tags=["Authentication"],
    )
    def post(self, request):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response({"error": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return Response({"error": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": "Logged out successfully."}, status=status.HTTP_200_OK)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get current user profile",
        operation_description="Returns the full profile of the currently authenticated user.",
        responses={
            200: openapi.Response(
                description="User profile",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_STRING, format="uuid"),
                        "email": openapi.Schema(type=openapi.TYPE_STRING),
                        "username": openapi.Schema(type=openapi.TYPE_STRING),
                        "first_name": openapi.Schema(type=openapi.TYPE_STRING),
                        "last_name": openapi.Schema(type=openapi.TYPE_STRING),
                        "phone": openapi.Schema(type=openapi.TYPE_STRING),
                        "bio": openapi.Schema(type=openapi.TYPE_STRING),
                        "avatar": openapi.Schema(type=openapi.TYPE_STRING, format="uri", nullable=True),
                        "is_email_verified": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "created_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                    },
                ),
            ),
        },
        security=[{"Bearer": []}],
        tags=["Profile"],
    )
    def get(self, request):
        user = request.user
        return Response(
            {
                "id": str(user.id),
                "email": user.email,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone,
                "bio": user.bio,
                "avatar": request.build_absolute_uri(user.avatar.url) if user.avatar else None,
                "is_email_verified": user.is_email_verified,
                "created_at": user.created_at,
            }
        )

    @swagger_auto_schema(
        operation_summary="Update current user profile",
        operation_description="Updates one or more profile fields. All fields are optional. To update avatar, send as multipart/form-data.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "first_name": openapi.Schema(type=openapi.TYPE_STRING, example="Ahmed"),
                "last_name": openapi.Schema(type=openapi.TYPE_STRING, example="Benali"),
                "phone": openapi.Schema(type=openapi.TYPE_STRING, example="+213555123456"),
                "bio": openapi.Schema(type=openapi.TYPE_STRING, example="Wheat farmer from Setif."),
                "avatar": openapi.Schema(type=openapi.TYPE_STRING, format="binary", description="Profile image file (multipart/form-data)"),
            },
        ),
        responses={
            200: openapi.Response(description="Profile updated successfully"),
            400: "Validation error",
        },
        security=[{"Bearer": []}],
        tags=["Profile"],
    )
    def patch(self, request):
        user = request.user
        allowed_fields = ["first_name", "last_name", "phone", "bio"]

        for field in allowed_fields:
            if field in request.data:
                setattr(user, field, request.data[field])

        if "avatar" in request.FILES:
            user.avatar = request.FILES["avatar"]

        user.save()

        return Response(
            {
                "message": "Profile updated successfully.",
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "phone": user.phone,
                    "bio": user.bio,
                    "avatar": request.build_absolute_uri(user.avatar.url) if user.avatar else None,
                },
            }
        )

    @swagger_auto_schema(
        operation_summary="Delete current user account",
        operation_description="Permanently deletes the authenticated user's account. This action is irreversible.",
        responses={
            204: "Account deleted successfully",
        },
        security=[{"Bearer": []}],
        tags=["Profile"],
    )
    def delete(self, request):
        request.user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Change password",
        operation_description="Changes the password of the currently authenticated user. Requires the old password for verification.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["old_password", "new_password", "confirm_new_password"],
            properties={
                "old_password": openapi.Schema(type=openapi.TYPE_STRING, format="password", example="OldPass123!"),
                "new_password": openapi.Schema(type=openapi.TYPE_STRING, format="password", example="NewPass456!"),
                "confirm_new_password": openapi.Schema(type=openapi.TYPE_STRING, format="password", example="NewPass456!"),
            },
        ),
        responses={
            200: "Password changed successfully",
            400: "Validation error",
            401: "Wrong old password",
        },
        security=[{"Bearer": []}],
        tags=["Profile"],
    )
    def post(self, request):
        user = request.user
        old_password = request.data.get("old_password", "")
        new_password = request.data.get("new_password", "")
        confirm_new_password = request.data.get("confirm_new_password", "")

        if not user.check_password(old_password):
            return Response({"error": "Old password is incorrect."}, status=status.HTTP_401_UNAUTHORIZED)

        if new_password != confirm_new_password:
            return Response({"error": "New passwords do not match."}, status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 8:
            return Response({"error": "Password must be at least 8 characters."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()

        return Response({"message": "Password changed successfully."}, status=status.HTTP_200_OK)


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Request password reset email",
        operation_description="Sends a password reset link to the given email address. The link expires in 1 hour. For security, always returns 200 even if the email does not exist.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email"],
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, format="email", example="farmer@nabat.com"),
            },
        ),
        responses={
            200: openapi.Response(
                description="Reset email sent (or silently ignored if email not found)",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
        },
        tags=["Password Reset"],
    )
    def post(self, request):
        email = request.data.get("email", "").strip().lower()

        try:
            user = User.objects.get(email=email)
            reset_token = PasswordResetToken.objects.create(user=user)
            reset_url = f"{settings.FRONTEND_URL}/reset-password/{reset_token.token}"

            html_message = render_to_string(
                "auth/password_reset_email.html",
                {
                    "user": user,
                    "reset_url": reset_url,
                    "year": timezone.now().year,
                },
            )

            send_mail(
                subject="Reset Your NABAT Password",
                message=strip_tags(html_message),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
        except User.DoesNotExist:
            pass

        return Response(
            {"message": "If an account with that email exists, a reset link has been sent."},
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Reset password using token",
        operation_description="Resets the user's password using the token received in the reset email. The token is a UUID found in the reset link URL.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["token", "new_password", "confirm_new_password"],
            properties={
                "token": openapi.Schema(type=openapi.TYPE_STRING, format="uuid", description="UUID token from the reset link URL", example="550e8400-e29b-41d4-a716-446655440000"),
                "new_password": openapi.Schema(type=openapi.TYPE_STRING, format="password", example="NewSecurePass123!"),
                "confirm_new_password": openapi.Schema(type=openapi.TYPE_STRING, format="password", example="NewSecurePass123!"),
            },
        ),
        responses={
            200: "Password reset successfully",
            400: "Invalid or expired token, or password mismatch",
        },
        tags=["Password Reset"],
    )
    def post(self, request):
        token = request.data.get("token")
        new_password = request.data.get("new_password", "")
        confirm_new_password = request.data.get("confirm_new_password", "")

        if not token:
            return Response({"error": "Token is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            reset_token = PasswordResetToken.objects.get(token=token, is_used=False)
        except PasswordResetToken.DoesNotExist:
            return Response({"error": "Invalid or already used token."}, status=status.HTTP_400_BAD_REQUEST)

        if reset_token.is_expired():
            return Response({"error": "This reset link has expired. Please request a new one."}, status=status.HTTP_400_BAD_REQUEST)

        if new_password != confirm_new_password:
            return Response({"error": "Passwords do not match."}, status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 8:
            return Response({"error": "Password must be at least 8 characters."}, status=status.HTTP_400_BAD_REQUEST)

        user = reset_token.user
        user.set_password(new_password)
        user.save()

        reset_token.is_used = True
        reset_token.save()

        return Response({"message": "Password has been reset successfully. You can now log in."}, status=status.HTTP_200_OK)


class GoogleOAuthView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Login / Register with Google OAuth",
        operation_description=(
            "Authenticates a user using a Google OAuth access token obtained from the Google OAuth2 flow on the frontend. "
            "If the Google account is new to NABAT, a new user is automatically created. "
            "Returns JWT tokens just like a normal login.\n\n"
            "**Frontend flow:**\n"
            "1. Implement Google Sign-In on the frontend (e.g. using `@react-oauth/google`)\n"
            "2. Get the Google access token after user approves\n"
            "3. Send that token to this endpoint"
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["access_token"],
            properties={
                "access_token": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="The Google OAuth2 access token returned by Google Sign-In on the frontend.",
                    example="ya29.a0AfH6SMBxxxxxx...",
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="Google login successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "is_new_user": openapi.Schema(type=openapi.TYPE_BOOLEAN, description="True if this is the first time this Google account was used on NABAT"),
                        "user": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "id": openapi.Schema(type=openapi.TYPE_STRING, format="uuid"),
                                "email": openapi.Schema(type=openapi.TYPE_STRING),
                                "first_name": openapi.Schema(type=openapi.TYPE_STRING),
                                "last_name": openapi.Schema(type=openapi.TYPE_STRING),
                                "avatar": openapi.Schema(type=openapi.TYPE_STRING, format="uri", nullable=True),
                            },
                        ),
                        "tokens": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "access": openapi.Schema(type=openapi.TYPE_STRING),
                                "refresh": openapi.Schema(type=openapi.TYPE_STRING),
                            },
                        ),
                    },
                ),
            ),
            400: "Missing or invalid Google token",
            503: "Google API unreachable",
        },
        tags=["OAuth"],
    )
    def post(self, request):
        access_token = request.data.get("access_token")

        if not access_token:
            return Response({"error": "Google access token is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            google_response = http_requests.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
        except http_requests.exceptions.RequestException:
            return Response({"error": "Could not reach Google. Try again later."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        if google_response.status_code != 200:
            return Response({"error": "Invalid Google token."}, status=status.HTTP_400_BAD_REQUEST)

        google_data = google_response.json()
        google_id = google_data.get("sub")
        email = google_data.get("email", "").lower()
        first_name = google_data.get("given_name", "")
        last_name = google_data.get("family_name", "")
        picture = google_data.get("picture", "")

        if not email:
            return Response({"error": "Could not retrieve email from Google."}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(google_id=google_id).first()
        is_new_user = False

        if not user:
            user = User.objects.filter(email=email).first()
            if user:
                user.google_id = google_id
                user.save()
            else:
                is_new_user = True
                user = User.objects.create_user(
                    email=email,
                    password=None,
                    first_name=first_name,
                    last_name=last_name,
                    google_id=google_id,
                    is_email_verified=True,
                )

        tokens = get_tokens_for_user(user)

        return Response(
            {
                "message": "Google login successful.",
                "is_new_user": is_new_user,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "avatar": user.avatar.url if user.avatar else picture or None,
                },
                "tokens": tokens,
            },
            status=status.HTTP_200_OK,
        )