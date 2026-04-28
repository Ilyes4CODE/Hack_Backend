from django.urls import path
from .views import (
    NearestCentersView,
    CenterListView,
    CenterCreateView,
    CenterDetailView,
    CenterManageView,
)

urlpatterns = [
    path('nearest/', NearestCentersView.as_view(), name='locator-nearest'),
    path('all/', CenterListView.as_view(), name='locator-list'),
    path('create/', CenterCreateView.as_view(), name='locator-create'),
    path('<int:pk>/', CenterDetailView.as_view(), name='locator-detail'),
    path('<int:pk>/manage/', CenterManageView.as_view(), name='locator-manage'),
]