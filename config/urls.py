from django.contrib import admin
from django.urls import path, include
from . import views 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'), 
    path('simulador/', include('simulador.urls')), 
    #path('dashboard/', include('dashboard.urls')),
    path('contato/', views.contato, name='contato'),
]
