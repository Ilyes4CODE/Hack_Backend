from django.urls import path
from .views import CalculateInputsView, CropStagesView, ITDASReferenceTableView

urlpatterns = [
    path('calculate/', CalculateInputsView.as_view()),
    path('crops-stages/', CropStagesView.as_view()),
    path('reference/', ITDASReferenceTableView.as_view()),
]