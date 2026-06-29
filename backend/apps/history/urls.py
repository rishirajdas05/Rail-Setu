from django.urls import path

from .views import RecentView

urlpatterns = [
    path("recent/", RecentView.as_view(), name="recent"),
]