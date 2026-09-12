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
    # ==========================================================
    # GRÁFICO 1
    # COMPARAÇÃO DE CUSTOS
    # ==========================================================

    grafico_custos = go.Figure()

    grafico_custos.add_trace(
        go.Bar(
            x=[
                "Energia",
                "Manutenção",
                "Paradas",
            ],
            y=[
                custo_energia_sem_iot,
                CUSTO_MANUTENCAO_SEM_IOT,
                custo_paradas_sem_iot,
            ],
            name="Sem IoT",
        )
    )

    grafico_custos.add_trace(
        go.Bar(
            x=[
                "Energia",
                "Manutenção",
                "Paradas",
            ],
            y=[
                custo_energia_com_iot,
                custo_manutencao_com_iot,
                custo_paradas_com_iot,
            ],
            name="Com IoT",
        )
    )

    grafico_custos.update_layout(
        title="Comparação de custos operacionais",
        xaxis_title="Categoria",
        yaxis_title="Custo (R$)",
        barmode="group",
        template="plotly_white",
    )

    grafico_custos_html = pio.to_html(
        grafico_custos,
        full_html=False
    )

    # ==========================================================
    # GRÁFICO 2
    # ECONOMIA POR CATEGORIA
    # ==========================================================

    grafico_economia = go.Figure()

    grafico_economia.add_trace(
        go.Bar(
            x=[
                "Energia",
                "Manutenção",
                "Paradas",
            ],
            y=[
                economia_energia,
                economia_manutencao,
                economia_paradas,
            ],
            name="Economia",
        )
    )

    grafico_economia.update_layout(
        title="Economia gerada pelo uso de IoT",
        xaxis_title="Categoria",
        yaxis_title="Economia (R$)",
        template="plotly_white",
    )

    grafico_economia_html = pio.to_html(
        grafico_economia,
        full_html=False
    )

    # ==========================================================
    # GRÁFICO 3
    # CUSTO TOTAL
    # ==========================================================

    grafico_total = go.Figure()

    grafico_total.add_trace(
        go.Pie(
            labels=[
                "Sem IoT",
                "Com IoT",
            ],
            values=[
                custo_total_sem_iot,
                custo_total_com_iot,
            ],
            hole=0.45,
        )
    )

    grafico_total.update_layout(
        title="Comparação do custo operacional total",
        template="plotly_white",
    )

    grafico_total_html = pio.to_html(
        grafico_total,
        full_html=False
    )

    # ==========================================================
    # PERCENTUAL DE ECONOMIA
    # ==========================================================

    if custo_total_sem_iot > 0:
        percentual_economia = (
            economia_total
            / custo_total_sem_iot
        ) * 100
    else:
        percentual_economia = 0

    # ==========================================================
    # CONTEXTO
    # ==========================================================

    contexto = {

        "custo_total_sem_iot":
            round(custo_total_sem_iot, 2),

        "custo_total_com_iot":
            round(custo_total_com_iot, 2),

        "economia_total":
            round(economia_total, 2),

        "percentual_economia":
            round(percentual_economia, 2),

        "economia_energia":
            round(economia_energia, 2),

        "economia_manutencao":
            round(economia_manutencao, 2),

        "economia_paradas":
            round(economia_paradas, 2),

        "grafico_custos":
            grafico_custos_html,

        "grafico_economia":
            grafico_economia_html,

        "grafico_total":
            grafico_total_html,
    }

    return render(
        request,
        "dashboard/index.html",
        contexto
    )