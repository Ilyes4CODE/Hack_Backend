from django.urls import path
from .views import (
    GalleryListView,
    GallerySubmitView,
    GalleryAdminListView,
    GalleryApproveView,
    GalleryDeleteView,
)

urlpatterns = [
    path('', GalleryListView.as_view()),
    path('submit/', GallerySubmitView.as_view()),
    path('admin/pending/', GalleryAdminListView.as_view()),
    path('admin/<int:pk>/approve/', GalleryApproveView.as_view()),
    path('admin/<int:pk>/delete/', GalleryDeleteView.as_view()),
]