from django.urls import path
from .views import NearestCentersView, CenterDetailView, CenterListView, CenterManageView

urlpatterns = [
    path('nearest/', NearestCentersView.as_view()),
    path('all/', CenterListView.as_view()),
    path('<int:pk>/', CenterDetailView.as_view()),
    path('<int:pk>/manage/', CenterManageView.as_view()),
]