from django.shortcuts import render
import pandas as pd
import numpy as np

def calcular_simulacao(request):
    if request.method == 'POST':
        num_maquinas = int(request.POST.get('num_maquinas', 1500))
        custo_hora_parada = float(request.POST.get('custo_hora_parada', 85))
        custo_sensor_iot = float(request.POST.get('custo_sensor_iot', 40))
    else:
        num_maquinas = 50
        custo_hora_parada = 1200.0
        custo_sensor_iot = 180.0

    dias_simulados = 30
    np.random.seed(42) 
    media_horas_perdidas_dia = num_maquinas * 0.04 
    
    horas_paradas_sem_iot = np.random.normal(loc=media_horas_perdidas_dia, scale=media_horas_perdidas_dia * 0.3, size=dias_simulados)
    horas_paradas_sem_iot = np.clip(horas_paradas_sem_iot, media_horas_perdidas_dia * 0.2, None)
    custo_diario_sem_iot = horas_paradas_sem_iot * custo_hora_parada
    reducao_tempo_parada = 0.15 
    
    horas_paradas_com_iot = horas_paradas_sem_iot * (1 - reducao_tempo_parada)
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
    investimento_mensal = num_maquinas * custo_sensor_iot
    resultado_liquido = economia_bruta - investimento_mensal
    
    if investimento_mensal > 0:
        roi = (resultado_liquido / investimento_mensal) * 100
    else:
        roi = 0

    if resultado_liquido >= 0:
        texto_economia = f"R$ {resultado_liquido:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        cor_economia = "text-success"
        titulo_resultado = "LUCRO LÍQUIDO MENSAL"
    else:
        texto_economia = f"- R$ {abs(resultado_liquido):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        cor_economia = "text-danger"
        titulo_resultado = "PREJUÍZO (MAU NEGÓCIO)"

    contexto = {
        'num_maquinas': num_maquinas,
        'custo_hora_parada': int(custo_hora_parada),
        'custo_sensor_iot': int(custo_sensor_iot),
        
        'titulo_resultado': titulo_resultado,
        'economia_mensal': texto_economia,
        'cor_economia': cor_economia,
        
        'roi': f"{roi:.1f}%",
        'dados_grafico_dias': df['Dia'].tolist(),
        'dados_grafico_sem_iot': df['Custo_Sem_IoT'].tolist(),
        'dados_grafico_com_iot': df['Custo_Com_IoT'].tolist(),
    }

    return render(request, 'simulador/resultado.html', contexto)