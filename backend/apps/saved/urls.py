from django.urls import path

from .views import SavedDeleteView, SavedListCreateView

urlpatterns = [
    path("saved/", SavedListCreateView.as_view(), name="saved-list-create"),
    path("saved/<int:pk>/", SavedDeleteView.as_view(), name="saved-delete"),
]