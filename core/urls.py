from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('especialista/', views.especialista_view, name='especialista'),
    path('login/', views.login_view, name='login'),
    path('registro/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('offline/', views.offline_view, name='offline'),
]
