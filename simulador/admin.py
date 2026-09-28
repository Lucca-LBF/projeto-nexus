from django.contrib import admin
from .models import MensagemContato

@admin.register(MensagemContato)
class MensagemContatoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'email', 'assunto', 'data_envio')
    search_fields = ('nome', 'email', 'assunto')