from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.views.generic import TemplateView

from apps.ml_views import ConfirmationPredictView, DelayPredictView, RankPredictView
from apps.accounts import google_oauth
from apps.availability import AvailabilityView, WeekAvailabilityView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", lambda r: JsonResponse({"status": "ok"}), name="health"),
    path("auth/google/login/", google_oauth.google_login, name="google-login"),
    path("auth/google/callback/", google_oauth.google_callback, name="google-callback"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/", include("apps.search.urls")),
    path("api/", include("apps.stations.urls")),
    path("api/", include("apps.trains.urls")),
    path("api/", include("apps.booking.urls")),
    path("api/", include("apps.chat.urls")),
    path("api/", include("apps.saved.urls")),
    path("api/", include("apps.alerts.urls")),
    path("api/", include("apps.analytics.urls")),
    path("api/", include("apps.history.urls")),
    path("api/predict/confirmation/", ConfirmationPredictView.as_view(), name="predict-confirmation"),
    path("api/predict/delay/", DelayPredictView.as_view(), name="predict-delay"),
    path("api/predict/rank/", RankPredictView.as_view(), name="predict-rank"),
    path("api/availability/week/", WeekAvailabilityView.as_view(), name="availability-week"),
    path("api/availability/", AvailabilityView.as_view(), name="availability"),
    path("status/", TemplateView.as_view(template_name="status.html"), name="status"),
    path("train/<str:number>/", TemplateView.as_view(template_name="train.html"), name="train-page"),
    path("login/", TemplateView.as_view(template_name="login.html"), name="login-page"),
    path("book/", TemplateView.as_view(template_name="book.html"), name="book-page"),
    path("pnr/", TemplateView.as_view(template_name="pnr.html"), name="pnr-page"),
    path("account/", TemplateView.as_view(template_name="account.html"), name="account-page"),
    path("dashboard/", TemplateView.as_view(template_name="dashboard.html"), name="dashboard-page"),
    path("predict/", TemplateView.as_view(template_name="predict.html"), name="predict-page"),
    path("board/", TemplateView.as_view(template_name="board.html"), name="board-page"),
    path("coaches/", TemplateView.as_view(template_name="coaches.html"), name="coaches-page"),
    path("", TemplateView.as_view(template_name="index.html"), name="home"),
]