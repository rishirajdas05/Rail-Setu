from django.urls import path

from .views import BookingDetailView, BookingListCreateView, PnrStatusView
from .ticket import TicketView
from .cancel import CancelBookingView

urlpatterns = [
    path("bookings/", BookingListCreateView.as_view(), name="booking-list-create"),
    path("bookings/<str:pnr>/ticket/", TicketView.as_view(), name="booking-ticket"),
    path("bookings/<str:pnr>/cancel/", CancelBookingView.as_view(), name="booking-cancel"),
    path("bookings/<str:pnr>/", BookingDetailView.as_view(), name="booking-detail"),
    path("pnr/<str:pnr>/", PnrStatusView.as_view(), name="pnr-status"),
]