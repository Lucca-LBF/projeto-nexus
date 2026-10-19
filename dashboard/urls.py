from django.urls import path
from . import views, relatorio

urlpatterns = [
    path('', views.dashboard, name='dashboard_home'),
    path('relatorio/', relatorio.relatorio, name='relatorio'),
]
