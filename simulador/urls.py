from django.urls import path
from . import views

urlpatterns = [
    path('resultado/', views.calcular_simulacao, name='resultado_simulacao'),
]