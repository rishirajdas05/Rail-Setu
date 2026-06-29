from django.contrib import admin

from .models import BookedPax, Booking, Passenger


class BookedPaxInline(admin.TabularInline):
    model = BookedPax
    extra = 0


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("pnr", "user", "train", "journey_date", "travel_class", "status")
    search_fields = ("pnr",)
    list_filter = ("status", "travel_class", "quota")
    inlines = [BookedPaxInline]


admin.site.register(Passenger)
