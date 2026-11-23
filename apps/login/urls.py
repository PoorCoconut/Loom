from django.urls import path
from . import views

app_name = 'login'
urlpatterns = [
    path('', views.login_view, name='login'),
    path('guest/', views.guest_view, name='guest'),
    path('logout/', views.logout_view, name='logout'),
]