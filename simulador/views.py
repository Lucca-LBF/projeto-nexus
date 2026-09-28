from django.shortcuts import render
import pandas as pd
import numpy as np

def calcular_simulacao(request):
    if request.method == 'POST':
        num_maquinas = int(request.POST.get('num_maquinas', 100))
        custo_hora_parada = float(request.POST.get('custo_hora_parada', 5000))
        custo_sensor_iot = float(request.POST.get('custo_sensor_iot', 300))
    else:
        num_maquinas = 100
        custo_hora_parada = 5000.0
        custo_sensor_iot = 300.0

    dias_simulados = 30
    np.random.seed(42) 

    # 1. LÓGICA DE INEFICIÊNCIA (Mais conservadora e realista)
    media_horas_perdidas_dia = num_maquinas * 0.02 
    
    horas_paradas_sem_iot = np.random.normal(loc=media_horas_perdidas_dia, scale=media_horas_perdidas_dia * 0.4, size=dias_simulados)
    horas_paradas_sem_iot = np.clip(horas_paradas_sem_iot, media_horas_perdidas_dia * 0.3, None)

    custo_diario_sem_iot = horas_paradas_sem_iot * custo_hora_parada

    # 2. O EFEITO DA IOT (Redução realista de 15%)
    reducao_tempo_parada = 0.15 
    
    horas_paradas_com_iot = horas_paradas_sem_iot * (1 - reducao_tempo_parada)
    
    ruido_iot = np.random.normal(loc=0, scale=media_horas_perdidas_dia * 0.05, size=dias_simulados)
    horas_paradas_com_iot = np.clip(horas_paradas_com_iot + ruido_iot, media_horas_perdidas_dia * 0.1, None)

    # 3. CÁLCULO DOS CUSTOS DIÁRIOS
    custo_diario_sensores = (num_maquinas * custo_sensor_iot) / dias_simulados
    custo_diario_com_iot = (horas_paradas_com_iot * custo_hora_parada) + custo_diario_sensores

    # 4. ORGANIZAÇÃO COM PANDAS E RESULTADOS MENSAIS
    df = pd.DataFrame({
        'Dia': range(1, dias_simulados + 1),
        'Custo_Sem_IoT': custo_diario_sem_iot,
        'Custo_Com_IoT': custo_diario_com_iot
    })

    total_gasto_antigo = df['Custo_Sem_IoT'].sum()
    total_gasto_novo = df['Custo_Com_IoT'].sum()
    economia_mensal = total_gasto_antigo - total_gasto_novo
    
    custo_total_sensores_mes = (custo_sensor_iot * num_maquinas)
    
    # 5. CÁLCULO DO ROI REAL (Fórmula financeira correta)
    if custo_total_sensores_mes > 0:
        roi = ((economia_mensal - custo_total_sensores_mes) / custo_total_sensores_mes) * 100
    else:
        roi = 0

    # 6. FORMATAÇÃO VISUAL E CORES
    if economia_mensal > 0:
        texto_economia = f"R$ {economia_mensal:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        cor_economia = "text-success"
    else:
        texto_economia = f"- R$ {abs(economia_mensal):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        cor_economia = "text-danger"

    contexto = {
        'num_maquinas': num_maquinas,
        'custo_hora_parada': int(custo_hora_parada),
        'custo_sensor_iot': int(custo_sensor_iot),
        'economia_mensal': texto_economia,
        'cor_economia': cor_economia,
        'roi': f"{roi:.1f}%",
        'dados_grafico_dias': df['Dia'].tolist(),
        'dados_grafico_sem_iot': df['Custo_Sem_IoT'].tolist(),
        'dados_grafico_com_iot': df['Custo_Com_IoT'].tolist(),
    }

    return render(request, 'simulador/resultado.html', contexto)