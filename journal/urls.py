from django.urls import path
from .views import (
    FieldLogListView,
    FieldLogDetailView,
    WeatherAlertListView,
    WeatherAlertMarkReadView,
)

urlpatterns = [
    path('logs/', FieldLogListView.as_view()),
    path('logs/<int:pk>/', FieldLogDetailView.as_view()),
    path('alerts/', WeatherAlertListView.as_view()),
    path('alerts/<int:pk>/read/', WeatherAlertMarkReadView.as_view()),
]