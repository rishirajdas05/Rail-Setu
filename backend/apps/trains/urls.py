from django.urls import path

from .views import RunningStatusView, StationBoardView, TrainDetailView, TrainSearchView
from .schedule_pdf import SchedulePdfView

urlpatterns = [
    path("station-board/", StationBoardView.as_view(), name="station-board"),
    path("train-search/", TrainSearchView.as_view(), name="train-search"),
    path("running-status/<str:number>/", RunningStatusView.as_view(), name="running-status"),
    path("trains/<str:number>/schedule/", SchedulePdfView.as_view(), name="train-schedule"),
    path("trains/<str:number>/", TrainDetailView.as_view(), name="train-detail"),
]