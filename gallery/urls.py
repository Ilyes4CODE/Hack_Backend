from django.urls import path
from .views import (
    PostListView,
    PostCreateView,
    PostDetailView,
    PostUpdateView,
    PostDeleteView,
    CommentCreateView,
    CommentDeleteView,
)

urlpatterns = [
    path('', PostListView.as_view(), name='gallery-list'),
    path('create/', PostCreateView.as_view(), name='gallery-create'),
    path('<uuid:pk>/', PostDetailView.as_view(), name='gallery-detail'),
    path('<uuid:pk>/update/', PostUpdateView.as_view(), name='gallery-update'),
    path('<uuid:pk>/delete/', PostDeleteView.as_view(), name='gallery-delete'),
    path('<uuid:pk>/comments/', CommentCreateView.as_view(), name='gallery-comment-create'),
    path('<uuid:pk>/comments/<uuid:comment_pk>/delete/', CommentDeleteView.as_view(), name='gallery-comment-delete'),
]