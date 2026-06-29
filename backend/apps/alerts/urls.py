from django.urls import path

from .views import AlertDeleteView, AlertListCreateView

urlpatterns = [
    path("alerts/", AlertListCreateView.as_view(), name="alert-list-create"),
    path("alerts/<int:pk>/", AlertDeleteView.as_view(), name="alert-delete"),
]