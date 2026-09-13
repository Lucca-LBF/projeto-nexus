from django.shortcuts import render
import pandas as pd
import numpy as np

def calcular_simulacao(request):
    # 1. RECEBER OS DADOS DO FORMULÁRIO
    if request.method == 'POST':
        num_maquinas = int(request.POST.get('num_maquinas', 100))
        custo_hora_parada = float(request.POST.get('custo_hora_parada', 5000))
        custo_sensor_iot = float(request.POST.get('custo_sensor_iot', 300)) # Valor padrão mais realista para sensor mensal
    else:
        num_maquinas = 100
        custo_hora_parada = 5000.0
        custo_sensor_iot = 300.0

    # 2. SIMULAÇÃO REALISTA COM NUMPY (Distribuição Normal com Ruído)
    dias_simulados = 30
    np.random.seed(42) 

    # Média realista de horas paradas por dia para o total da fábrica (ex: ~12h/dia no total da frota sem IoT)
    horas_base_diarias = np.random.normal(loc=12.0, scale=3.0, size=dias_simulados)
    horas_base_diarias = np.clip(horas_base_diarias, 2.0, 25.0) # Evita valores negativos ou absurdos

    # Cenário Sem IoT: Custo diário baseado nas horas paradas
    custo_diario_sem_iot = horas_base_diarias * custo_hora_parada

    # Cenário Com IoT: Sensores reduzem as falhas inesperadas em 75%
    horas_paradas_com_iot = horas_base_diarias * 0.25
    
    # Custo dos sensores distribuído por dia do mês
    custo_diario_sensores = (num_maquinas * custo_sensor_iot) / dias_simulados
    custo_diario_com_iot = (horas_paradas_com_iot * custo_hora_parada) + custo_diario_sensores

    # 3. ORGANIZAÇÃO COM PANDAS
    df = pd.DataFrame({
        'Dia': range(1, dias_simulados + 1),
        'Custo_Sem_IoT': custo_diario_sem_iot,
        'Custo_Com_IoT': custo_diario_com_iot
    })

    # 4. TOTAIS E ROI
    total_gasto_antigo = df['Custo_Sem_IoT'].sum()
    total_gasto_novo = df['Custo_Com_IoT'].sum()
    economia_mensal = total_gasto_antigo - total_gasto_novo
    
    custo_total_sensores_mes = (custo_sensor_iot * num_maquinas)
    if custo_total_sensores_mes > 0:
        roi = (economia_mensal / custo_total_sensores_mes) * 100
    else:
        roi = 0

    # 5. CONTEXTO PARA O HTML
    contexto = {
        'num_maquinas': num_maquinas,
        'custo_hora_parada': int(custo_hora_parada),
        'custo_sensor_iot': int(custo_sensor_iot),
        'economia_mensal': f"R$ {economia_mensal:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
        'roi': f"{roi:.1f}%",
        'dados_grafico_dias': df['Dia'].tolist(),
        'dados_grafico_sem_iot': df['Custo_Sem_IoT'].tolist(),
        'dados_grafico_com_iot': df['Custo_Com_IoT'].tolist(),
    }

    return render(request, 'simulador/resultado.html', contexto)