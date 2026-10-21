from django.urls import path
from . import views

urlpatterns = [
    path('', views.formulario_simulador, name='formulario_simulador'),
    path('resultado/', views.calcular_simulacao, name='resultado_simulacao'),
    path('relatorio/', views.relatorio, name='relatorio'),
]