from django.shortcuts import render
from simulador.models import MensagemContato 

def home(request):
    return render(request, 'home.html')


    return render(request, 'contato.html', {'sucesso': sucesso})
