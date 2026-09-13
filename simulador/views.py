from django.shortcuts import render
import pandas as pd
import numpy as np

def calcular_simulacao(request):
    # 1. RECEBER OS DADOS
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

    chance_falha = 0.05 
    falhas_diarias_por_maquina = np.random.poisson(lam=chance_falha, size=dias_simulados)
    horas_paradas_sem_iot = falhas_diarias_por_maquina * num_maquinas * 2
    custo_diario_sem_iot = horas_paradas_sem_iot * custo_hora_parada
    reducao_falhas = 0.20 
    horas_paradas_com_iot = horas_paradas_sem_iot * reducao_falhas
    custo_diario_sensores = (num_maquinas * custo_sensor_iot) / dias_simulados
    custo_diario_com_iot = (horas_paradas_com_iot * custo_hora_parada) + custo_diario_sensores

    df = pd.DataFrame({
        'Dia': range(1, dias_simulados + 1),
        'Custo_Sem_IoT': custo_diario_sem_iot,
        'Custo_Com_IoT': custo_diario_com_iot
    })

    total_gasto_antigo = df['Custo_Sem_IoT'].sum()
    total_gasto_novo = df['Custo_Com_IoT'].sum()
    economia_mensal = total_gasto_antigo - total_gasto_novo
    custo_total_sensores_mes = (custo_sensor_iot * num_maquinas)
    if custo_total_sensores_mes > 0:
        roi = (economia_mensal / custo_total_sensores_mes) * 100
    else:
        roi = 0
    contexto = {
        'num_maquinas': num_maquinas,
        'custo_hora_parada': int(custo_hora_parada), # Envia de volta pro form
        'custo_sensor_iot': int(custo_sensor_iot),   # Envia de volta pro form
        'economia_mensal': f"R$ {economia_mensal:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
        'roi': f"{roi:.1f}%",
        'dados_grafico_dias': df['Dia'].tolist(),
        'dados_grafico_sem_iot': df['Custo_Sem_IoT'].tolist(),
        'dados_grafico_com_iot': df['Custo_Com_IoT'].tolist(),
    }

    return render(request, 'simulador/resultado.html', contexto)