from django.urls import path

from . import views

app_name = "discover"
urlpatterns = [
    path("discover/", views.discover_view, name="discover"),
    path("collections/", views.collections_view, name="collections"),
    path("discover/toggle/<str:kind>/<int:story_id>/", views.toggle_view, name="toggle"),
]
