from django.shortcuts import render
from .models import SensorData

import plotly.graph_objects as go
import plotly.io as pio


def dashboard(request):

    # ==========================================================
    # BUSCAR DADOS DO BANCO
    # ==========================================================

    dados = SensorData.objects.all().order_by("data_hora")

    # ==========================================================
    # CONFIGURAÇÕES DE CUSTO
    # ==========================================================

    # Valores hipotéticos para a demonstração
    # Depois vocês podem alterar para valores reais.

    PRECO_KWH = 0.85

    # Custo estimado de manutenção sem IoT
    CUSTO_MANUTENCAO_SEM_IOT = 2500.00

    # Custo estimado de cada parada sem IoT
    CUSTO_PARADA_SEM_IOT = 800.00

    # ==========================================================
    # DADOS
    # ==========================================================

    datas = [
        d.data_hora.strftime("%d/%m/%Y")
        for d in dados
    ]

    energias = [
        d.energia
        for d in dados
    ]

    temperaturas = [
        d.temperatura
        for d in dados
    ]

    producoes = [
        d.producao
        for d in dados
    ]

    # ==========================================================
    # CUSTO DE ENERGIA
    # ==========================================================

    consumo_total_energia = sum(energias)

    custo_energia_com_iot = (
        consumo_total_energia * PRECO_KWH
    )

    # Estimativa de consumo sem IoT
    # Aqui consideramos que a empresa consumiria 20% a mais.
    consumo_sem_iot = consumo_total_energia * 1.20

    custo_energia_sem_iot = (
        consumo_sem_iot * PRECO_KWH
    )

    economia_energia = (
        custo_energia_sem_iot
        - custo_energia_com_iot
    )

    # ==========================================================
    # MANUTENÇÃO
    # ==========================================================

    # Com IoT: manutenção preventiva
    # Consideramos uma redução de 30%.
    custo_manutencao_com_iot = (
        CUSTO_MANUTENCAO_SEM_IOT * 0.70
    )

    economia_manutencao = (
        CUSTO_MANUTENCAO_SEM_IOT
        - custo_manutencao_com_iot
    )

    # ==========================================================
    # PARADAS
    # ==========================================================

    # Exemplo:
    # sem IoT -> 10 paradas
    # com IoT -> 4 paradas

    paradas_sem_iot = 10
    paradas_com_iot = 4

    custo_paradas_sem_iot = (
        paradas_sem_iot
        * CUSTO_PARADA_SEM_IOT
    )

    custo_paradas_com_iot = (
        paradas_com_iot
        * CUSTO_PARADA_SEM_IOT
    )

    economia_paradas = (
        custo_paradas_sem_iot
        - custo_paradas_com_iot
    )

    # ==========================================================
    # ECONOMIA TOTAL
    # ==========================================================

    economia_total = (
        economia_energia
        + economia_manutencao
        + economia_paradas
    )

    