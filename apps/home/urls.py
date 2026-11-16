from django.urls import path
from . import views

app_name = 'home'
urlpatterns = [
    path('', views.home_view, name='home'),
    path('stories/new/', views.create_story, name='create_story'),
]
