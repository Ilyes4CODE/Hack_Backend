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
import re

from .models import PasswordResetToken, EmailVerificationCode

User = get_user_model()


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


def is_valid_email(value):
    return re.match(r'^[^@]+@[^@]+\.[^@]+$', value) is not None


def is_valid_phone(value):
    return re.match(r'^\+?[0-9]{9,15}$', value) is not None


def send_verification_email(user, code):
    html_message = render_to_string(
        "auth/email_verification.html",
        {
            "user": user,
            "code": code,
            "year": timezone.now().year,
        },
    )
    send_mail(
        subject="Your NABTA Verification Code",
        message=f"Your verification code is: {code}. It expires in 15 minutes.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Register a new user",
        operation_description=(
            "Creates a new NABTA farmer account using either **email** or **phone number**.\n\n"
            "- If registering with **email**: a 6-digit verification code is sent to the email. Use `/auth/verify-email/` to verify.\n"
            "- If registering with **phone**: account is created directly, no code is sent.\n\n"
            "Provide either `email` or `phone` — not both. `identifier` is used for login."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["identifier", "password", "confirm_password"],
            properties={
                "identifier": openapi.Schema(type=openapi.TYPE_STRING, example="farmer@nabta.com or +213555123456", description="Email address or phone number"),
                "password": openapi.Schema(type=openapi.TYPE_STRING, format="password", example="StrongPass123!"),
                "confirm_password": openapi.Schema(type=openapi.TYPE_STRING, format="password", example="StrongPass123!"),
                "first_name": openapi.Schema(type=openapi.TYPE_STRING, example="Ahmed"),
                "last_name": openapi.Schema(type=openapi.TYPE_STRING, example="Benali"),
            },
        ),
        responses={
            201: openapi.Response(
                description="Registration successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "registration_type": openapi.Schema(type=openapi.TYPE_STRING, enum=["email", "phone"]),
                        "email_verification_required": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "user": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "id": openapi.Schema(type=openapi.TYPE_STRING, format="uuid"),
                                "email": openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                "phone": openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                "role": openapi.Schema(type=openapi.TYPE_STRING, example="farmer"),
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
            400: "Validation error",
        },
        tags=["Authentication"],
    )
    def post(self, request):
        identifier = request.data.get("identifier", "").strip()
        password = request.data.get("password", "")
        confirm_password = request.data.get("confirm_password", "")
        first_name = request.data.get("first_name", "")
        last_name = request.data.get("last_name", "")

        if not identifier:
            return Response({"error": "Email or phone number is required."}, status=status.HTTP_400_BAD_REQUEST)

        if not password:
            return Response({"error": "Password is required."}, status=status.HTTP_400_BAD_REQUEST)

        if password != confirm_password:
            return Response({"error": "Passwords do not match."}, status=status.HTTP_400_BAD_REQUEST)

        if len(password) < 8:
            return Response({"error": "Password must be at least 8 characters."}, status=status.HTTP_400_BAD_REQUEST)

        registration_type = None

        if is_valid_email(identifier):
            registration_type = "email"
            if User.objects.filter(email=identifier.lower()).exists():
                return Response({"error": "An account with this email already exists."}, status=status.HTTP_400_BAD_REQUEST)
            user = User.objects.create_user(
                email=identifier.lower(),
                password=password,
                first_name=first_name,
                last_name=last_name,
                role='farmer',
            )
            code = EmailVerificationCode.generate_code()
            EmailVerificationCode.objects.create(user=user, code=code)
            try:
                send_verification_email(user, code)
            except Exception:
                pass

        elif is_valid_phone(identifier):
            registration_type = "phone"
            if User.objects.filter(phone=identifier).exists():
                return Response({"error": "An account with this phone number already exists."}, status=status.HTTP_400_BAD_REQUEST)
            user = User.objects.create_user(
                phone=identifier,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role='farmer',
            )

        else:
            return Response({"error": "Provide a valid email address or phone number."}, status=status.HTTP_400_BAD_REQUEST)

        tokens = get_tokens_for_user(user)

        return Response(
            {
                "message": "Account created successfully. Welcome to NABTA!" if registration_type == "phone" else "Account created. Please verify your email.",
                "registration_type": registration_type,
                "email_verification_required": registration_type == "email",
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "phone": user.phone,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role,
                },
                "tokens": tokens,
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Verify email with 6-digit code",
        operation_description="Submit the 6-digit code sent to the user's email after registration. Marks the account as email-verified.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["code"],
            properties={
                "code": openapi.Schema(type=openapi.TYPE_STRING, example="483921", description="6-digit verification code sent to the email"),
            },
        ),
        responses={
            200: "Email verified successfully",
            400: "Invalid or expired code",
        },
        security=[{"Bearer": []}],
        tags=["Authentication"],
    )
    def post(self, request):
        code = request.data.get("code", "").strip()

        if not code:
            return Response({"error": "Verification code is required."}, status=status.HTTP_400_BAD_REQUEST)

        if request.user.is_email_verified:
            return Response({"message": "Email is already verified."}, status=status.HTTP_200_OK)

        try:
            verification = EmailVerificationCode.objects.filter(
                user=request.user,
                code=code,
                is_used=False
            ).latest('created_at')
        except EmailVerificationCode.DoesNotExist:
            return Response({"error": "Invalid verification code."}, status=status.HTTP_400_BAD_REQUEST)

        if verification.is_expired():
            return Response({"error": "Verification code has expired. Request a new one."}, status=status.HTTP_400_BAD_REQUEST)

        verification.is_used = True
        verification.save()

        request.user.is_email_verified = True
        request.user.save()

        return Response({"message": "Email verified successfully."}, status=status.HTTP_200_OK)


class ResendVerificationCodeView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Resend email verification code",
        operation_description="Generates and sends a new 6-digit verification code to the user's email. Previous codes are invalidated.",
        responses={
            200: "New code sent",
            400: "Email already verified or user has no email",
        },
        security=[{"Bearer": []}],
        tags=["Authentication"],
    )
    def post(self, request):
        user = request.user

        if user.is_email_verified:
            return Response({"message": "Email is already verified."}, status=status.HTTP_400_BAD_REQUEST)

        if not user.email:
            return Response({"error": "No email address associated with this account."}, status=status.HTTP_400_BAD_REQUEST)

        EmailVerificationCode.objects.filter(user=user, is_used=False).update(is_used=True)

        code = EmailVerificationCode.generate_code()
        EmailVerificationCode.objects.create(user=user, code=code)

        try:
            send_verification_email(user, code)
        except Exception:
            return Response({"error": "Failed to send email. Try again later."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": "A new verification code has been sent to your email."}, status=status.HTTP_200_OK)


class LoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Login with email or phone",
        operation_description="Authenticates a user using either email or phone number plus password. Returns JWT tokens.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["identifier", "password"],
            properties={
                "identifier": openapi.Schema(type=openapi.TYPE_STRING, example="farmer@nabta.com or +213555123456", description="Email address or phone number"),
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
                                "email": openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                "phone": openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                "first_name": openapi.Schema(type=openapi.TYPE_STRING),
                                "last_name": openapi.Schema(type=openapi.TYPE_STRING),
                                "role": openapi.Schema(type=openapi.TYPE_STRING),
                                "is_email_verified": openapi.Schema(type=openapi.TYPE_BOOLEAN),
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
            400: "Missing fields",
            401: "Invalid credentials",
        },
        tags=["Authentication"],
    )
    def post(self, request):
        identifier = request.data.get("identifier", "").strip()
        password = request.data.get("password", "")

        if not identifier or not password:
            return Response({"error": "Identifier and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        user = None

        if is_valid_email(identifier):
            user = User.objects.filter(email=identifier.lower()).first()
        elif is_valid_phone(identifier):
            user = User.objects.filter(phone=identifier).first()
        else:
            return Response({"error": "Provide a valid email or phone number."}, status=status.HTTP_400_BAD_REQUEST)

        if not user or not user.check_password(password):
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
                    "phone": user.phone,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role,
                    "is_email_verified": user.is_email_verified,
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
        operation_description="Blacklists the provided refresh token, effectively logging the user out.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["refresh"],
            properties={
                "refresh": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={200: "Logged out successfully", 400: "Invalid or missing refresh token"},
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
        responses={200: "User profile"},
        security=[{"Bearer": []}],
        tags=["Profile"],
    )
    def get(self, request):
        user = request.user
        return Response(
            {
                "id": str(user.id),
                "email": user.email,
                "phone": user.phone,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
                "bio": user.bio,
                "avatar": request.build_absolute_uri(user.avatar.url) if user.avatar else None,
                "is_email_verified": user.is_email_verified,
                "created_at": user.created_at,
            }
        )

    @swagger_auto_schema(
        operation_summary="Update current user profile",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "first_name": openapi.Schema(type=openapi.TYPE_STRING),
                "last_name": openapi.Schema(type=openapi.TYPE_STRING),
                "phone": openapi.Schema(type=openapi.TYPE_STRING),
                "bio": openapi.Schema(type=openapi.TYPE_STRING),
                "avatar": openapi.Schema(type=openapi.TYPE_STRING, format="binary"),
            },
        ),
        responses={200: "Profile updated", 400: "Validation error"},
        security=[{"Bearer": []}],
        tags=["Profile"],
    )
    def patch(self, request):
        user = request.user
        for field in ["first_name", "last_name", "phone", "bio"]:
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
                    "phone": user.phone,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role,
                    "bio": user.bio,
                    "avatar": request.build_absolute_uri(user.avatar.url) if user.avatar else None,
                },
            }
        )

    @swagger_auto_schema(
        operation_summary="Delete current user account",
        responses={204: "Account deleted"},
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
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["old_password", "new_password", "confirm_new_password"],
            properties={
                "old_password": openapi.Schema(type=openapi.TYPE_STRING, format="password"),
                "new_password": openapi.Schema(type=openapi.TYPE_STRING, format="password"),
                "confirm_new_password": openapi.Schema(type=openapi.TYPE_STRING, format="password"),
            },
        ),
        responses={200: "Password changed", 400: "Validation error", 401: "Wrong old password"},
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
        operation_summary="Request password reset",
        operation_description="Sends a password reset link to the given email. Always returns 200 for security.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email"],
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, format="email"),
            },
        ),
        responses={200: "Reset email sent"},
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
                {"user": user, "reset_url": reset_url, "year": timezone.now().year},
            )

            send_mail(
                subject="Reset Your NABTA Password",
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
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["token", "new_password", "confirm_new_password"],
            properties={
                "token": openapi.Schema(type=openapi.TYPE_STRING, format="uuid"),
                "new_password": openapi.Schema(type=openapi.TYPE_STRING, format="password"),
                "confirm_new_password": openapi.Schema(type=openapi.TYPE_STRING, format="password"),
            },
        ),
        responses={200: "Password reset successfully", 400: "Invalid or expired token"},
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
            return Response({"error": "This reset link has expired."}, status=status.HTTP_400_BAD_REQUEST)

        if new_password != confirm_new_password:
            return Response({"error": "Passwords do not match."}, status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 8:
            return Response({"error": "Password must be at least 8 characters."}, status=status.HTTP_400_BAD_REQUEST)

        user = reset_token.user
        user.set_password(new_password)
        user.save()

        reset_token.is_used = True
        reset_token.save()

        return Response({"message": "Password has been reset successfully."}, status=status.HTTP_200_OK)


class GoogleOAuthView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Login / Register with Google OAuth",
        operation_description=(
            "Authenticates a user using a Google OAuth access token. "
            "If the Google account is new to NABTA, a new user is automatically created."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["access_token"],
            properties={
                "access_token": openapi.Schema(type=openapi.TYPE_STRING, example="ya29.a0AfH6SMBxxxxxx..."),
            },
        ),
        responses={
            200: "Google login successful",
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
                    "role": user.role,
                    "avatar": user.avatar.url if user.avatar else picture or None,
                },
                "tokens": tokens,
            },
            status=status.HTTP_200_OK,
        )


class CreateAdminView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Create a new admin account",
        operation_description="Allows an existing admin to create a new admin account. Only admins can access this.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email", "password", "confirm_password"],
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, format="email", example="newadmin@nabta.com"),
                "password": openapi.Schema(type=openapi.TYPE_STRING, format="password"),
                "confirm_password": openapi.Schema(type=openapi.TYPE_STRING, format="password"),
                "first_name": openapi.Schema(type=openapi.TYPE_STRING),
                "last_name": openapi.Schema(type=openapi.TYPE_STRING),
                "phone": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={
            201: "Admin created",
            400: "Validation error",
            403: "Only admins can access this",
        },
        security=[{"Bearer": []}],
        tags=["Admin"],
    )
    def post(self, request):
        if request.user.role != 'admin':
            return Response({"error": "Only admins can create admin accounts."}, status=status.HTTP_403_FORBIDDEN)

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

        new_admin = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone=phone or None,
            role='admin',
        )

        return Response(
            {
                "message": "Admin account created successfully.",
                "admin": {
                    "id": str(new_admin.id),
                    "email": new_admin.email,
                    "first_name": new_admin.first_name,
                    "last_name": new_admin.last_name,
                    "role": new_admin.role,
                    "is_staff": new_admin.is_staff,
                    "created_at": new_admin.created_at,
                },
            },
            status=status.HTTP_201_CREATED,
        )