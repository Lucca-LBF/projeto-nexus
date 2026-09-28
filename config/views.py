from django.shortcuts import render
from simulador.models import MensagemContato 

def home(request):
    return render(request, 'home.html')

def contato(request):
    sucesso = False 
    
    if request.method == 'POST':
        nome_digitado = request.POST.get('nome')
        email_digitado = request.POST.get('email')
        assunto_digitado = request.POST.get('assunto')
        mensagem_digitada = request.POST.get('mensagem')

        MensagemContato.objects.create(
            nome=nome_digitado,
            email=email_digitado,
            assunto=assunto_digitado,
            mensagem=mensagem_digitada
        )
        sucesso = True
    return render(request, 'contato.html', {'sucesso': sucesso})