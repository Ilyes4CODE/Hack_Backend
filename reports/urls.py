from django.urls import path
from .views import GenerateReportView, ReportListView, ReportPreviewView

urlpatterns = [
    path('generate/', GenerateReportView.as_view()),
    path('', ReportListView.as_view()),
    path('preview/', ReportPreviewView.as_view()),
]