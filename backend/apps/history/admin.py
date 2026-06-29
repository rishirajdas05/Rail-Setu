from django.contrib import admin

from .models import RecentItem


@admin.register(RecentItem)
class RecentItemAdmin(admin.ModelAdmin):
    list_display = ("user", "kind", "key", "label", "viewed_at")
    list_filter = ("kind",)
    search_fields = ("key", "label", "user__username")