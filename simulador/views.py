from django.shortcuts import render
import pandas as pd
import numpy as np

def calcular_simulacao(request):

    if request.method == 'POST':
        num_maquinas = int(request.POST.get('num_maquinas', 10))
        custo_hora_parada = float(request.POST.get('custo_hora_parada', 5000))
        custo_sensor_iot = float(request.POST.get('custo_sensor_iot', 150))
    else:
        num_maquinas = 10
        custo_hora_parada = 5000.0
        custo_sensor_iot = 150.0

    dias_simulados = 30
    np.random.seed(42) 

    horas_paradas_sem_iot = np.random.poisson(lam=1.5, size=dias_simulados) * num_maquinas
    custo_diario_sem_iot = horas_paradas_sem_iot * custo_hora_parada

    reducao_falhas = 0.20 
    horas_paradas_com_iot = horas_paradas_sem_iot * reducao_falhas
    custo_manutencao_sensores = num_maquinas * custo_sensor_iot
    
    custo_diario_com_iot = (horas_paradas_com_iot * custo_hora_parada) + custo_manutencao_sensores

    df = pd.DataFrame({
        'Dia': range(1, dias_simulados + 1),
        'Custo_Sem_IoT': custo_diario_sem_iot,
        'Custo_Com_IoT': custo_diario_com_iot
    })

    total_gasto_antigo = df['Custo_Sem_IoT'].sum()
    total_gasto_novo = df['Custo_Com_IoT'].sum()
    economia_mensal = total_gasto_antigo - total_gasto_novo
    roi = (economia_mensal / (custo_sensor_iot * num_maquinas * dias_simulados)) * 100

    contexto = {
        'num_maquinas': num_maquinas,
        'economia_mensal': f"R$ {economia_mensal:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
        'roi': f"{roi:.1f}%",
        'dados_grafico_dias': df['Dia'].tolist(),
        'dados_grafico_sem_iot': df['Custo_Sem_IoT'].tolist(),
        'dados_grafico_com_iot': df['Custo_Com_IoT'].tolist(),
    }

    return render(request, 'simulador/resultado.html', contexto)