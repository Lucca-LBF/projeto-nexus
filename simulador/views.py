from django.shortcuts import render, redirect
import pandas as pd
import numpy as np
from .forms import DadosEmpresaForm

# chave da sessão onde ficam os dados da última simulação
CHAVE_SESSAO = 'simulacao'


def calcular_simulacao(request):
    if request.method == 'POST':
        num_maquinas = int(request.POST.get('num_maquinas', 100))
        custo_hora_parada = float(request.POST.get('custo_hora_parada', 5000))
        custo_sensor_iot = float(request.POST.get('custo_sensor_iot', 300))
        dias_simulados = int(request.POST.get('tempo_amostra', 30))
        tipo_industria = request.POST.get('tipo_industria', 'padrao')

        request.session[CHAVE_SESSAO] = {
            'num_maquinas': num_maquinas,
            'custo_hora_parada': custo_hora_parada,
            'custo_sensor_iot': custo_sensor_iot,
            'tempo_amostra': dias_simulados,
            'tipo_industria': tipo_industria,
        }
    else:
        salvo = request.session.get(CHAVE_SESSAO, {})
        num_maquinas = salvo.get('num_maquinas', 40)
        custo_hora_parada = salvo.get('custo_hora_parada', 1500.0)
        custo_sensor_iot = salvo.get('custo_sensor_iot', 35.0)
        dias_simulados = salvo.get('tempo_amostra', 30)
        tipo_industria = salvo.get('tipo_industria', 'padrao')

    np.random.seed(42)

    if tipo_industria == 'textil':
        taxa_falha_base = 0.06  
        reducao_iot = 0.12     
        nome_industria = "Indústria Têxtil"
        
    elif tipo_industria == 'pesada':
        taxa_falha_base = 0.03
        reducao_iot = 0.25     
        nome_industria = "Manufatura Pesada"
        
    elif tipo_industria == 'refrigeracao':
        taxa_falha_base = 0.04 
        reducao_iot = 0.35   
        nome_industria = "Frio Industrial e Refrigeração"
        
    else:
        taxa_falha_base = 0.04
        reducao_iot = 0.15
        nome_industria = "Simulação Padrão"

    media_horas_perdidas_dia = num_maquinas * taxa_falha_base 
    
    horas_paradas_sem_iot = np.random.normal(loc=media_horas_perdidas_dia, scale=media_horas_perdidas_dia * 0.3, size=dias_simulados)
    horas_paradas_sem_iot = np.clip(horas_paradas_sem_iot, media_horas_perdidas_dia * 0.2, None)
    custo_diario_sem_iot = horas_paradas_sem_iot * custo_hora_parada

    horas_paradas_com_iot = horas_paradas_sem_iot * (1 - reducao_iot)
    ruido_iot = np.random.normal(loc=0, scale=media_horas_perdidas_dia * 0.05, size=dias_simulados)
    horas_paradas_com_iot = np.clip(horas_paradas_com_iot + ruido_iot, media_horas_perdidas_dia * 0.1, None)
    custo_diario_com_iot = horas_paradas_com_iot * custo_hora_parada

    df = pd.DataFrame({
        'Dia': range(1, dias_simulados + 1),
        'Custo_Sem_IoT': custo_diario_sem_iot,
        'Custo_Com_IoT': custo_diario_com_iot
    })


    total_operacional_antigo = df['Custo_Sem_IoT'].sum()
    total_operacional_novo = df['Custo_Com_IoT'].sum()
    economia_bruta = total_operacional_antigo - total_operacional_novo
    meses_simulados = dias_simulados / 30
    investimento_periodo = (num_maquinas * custo_sensor_iot) * meses_simulados
    
    resultado_liquido = economia_bruta - investimento_periodo
    
    if investimento_periodo > 0:
        roi = (resultado_liquido / investimento_periodo) * 100
    else:
        roi = 0

    if resultado_liquido >= 0:
        texto_economia = f"R$ {resultado_liquido:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        cor_economia = "text-success"
        titulo_resultado = f"LUCRO LÍQUIDO ({dias_simulados} DIAS)"
    else:
        texto_economia = f"- R$ {abs(resultado_liquido):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        cor_economia = "text-danger"
        titulo_resultado = f"PREJUÍZO ({dias_simulados} DIAS)"

    contexto = {
        'num_maquinas': num_maquinas,
        'custo_hora_parada': int(custo_hora_parada),
        'custo_sensor_iot': int(custo_sensor_iot),
        'dias_simulados': dias_simulados,
        'nome_industria': nome_industria,
        
        'titulo_resultado': titulo_resultado,
        'economia_mensal': texto_economia,
        'cor_economia': cor_economia,
        'roi': f"{roi:.1f}%",
        'dados_grafico_dias': df['Dia'].tolist(),
        'dados_grafico_sem_iot': df['Custo_Sem_IoT'].tolist(),
        'dados_grafico_com_iot': df['Custo_Com_IoT'].tolist(),
    }
    return render(request, 'simulador/resultado.html', contexto)


def formulario_simulador(request):
    # ?nova=1 apaga a simulação guardada e volta ao formulário padrão
    if request.GET.get('nova'):
        request.session.pop(CHAVE_SESSAO, None)
        return redirect('formulario_simulador')

    salvo = request.session.get(CHAVE_SESSAO)
    form = DadosEmpresaForm(initial=salvo) if salvo else DadosEmpresaForm()
    return render(request, 'simulador/simulador.html', {'form': form, 'tem_memoria': bool(salvo)})