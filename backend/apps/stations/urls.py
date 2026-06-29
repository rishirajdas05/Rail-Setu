from django.urls import path

from .views import StationSuggestView

urlpatterns = [
    path("stations/", StationSuggestView.as_view(), name="station-suggest"),
]