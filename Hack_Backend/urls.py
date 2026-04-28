from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="NABAT API",
        default_version="v1",
        description=(
            "## NABAT – Agricultural Intelligence Platform\n\n"
            "### Authentication\n"
            "Most endpoints require a JWT Bearer token. After login or register, copy the `access` token "
            "and click **Authorize** (top right), then enter: `Bearer <your_access_token>`\n\n"
            "### Token Refresh\n"
            "Access tokens expire. Use `POST /auth/token/refresh/` with your `refresh` token to get a new `access` token.\n\n"
            "### Google OAuth\n"
            "Use `POST /auth/google/` with a Google access token from your frontend Google Sign-In flow."
        ),
        contact=openapi.Contact(email="support@nabat.com"),
        license=openapi.License(name="Proprietary"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
    authentication_classes=[],
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/", include("Auth.urls")),
    path("locator/", include("locator.urls")),
    path("journal/", include("journal.urls")),
    path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    path("swagger.json", schema_view.without_ui(cache_timeout=0), name="schema-json"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)