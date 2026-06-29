from django.urls import path

from .views import TrainSearchView

urlpatterns = [
    path("trains/search/", TrainSearchView.as_view(), name="train-search"),
]