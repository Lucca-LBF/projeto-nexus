from django.shortcuts import render
from .models import EconomiaIoT

import plotly.graph_objects as go
import plotly.io as pio


def dashboard(request):

    dados = EconomiaIoT.objects.first()

    if dados:

        total_sem_iot = (
            dados.energia_sem_iot
            + dados.manutencao_sem_iot
            + dados.paradas_sem_iot
        )

        total_com_iot = (
            dados.energia_com_iot
            + dados.manutencao_com_iot
            + dados.paradas_com_iot
        )

        economia = total_sem_iot - total_com_iot

        percentual_economia = (
            (economia / total_sem_iot) * 100
            if total_sem_iot > 0
            else 0
        )

    else:

        total_sem_iot = 0
        total_com_iot = 0
        economia = 0
        percentual_economia = 0

    # GRÁFICO DE COMPARAÇÃO

    grafico_custos = go.Figure()

    grafico_custos.add_trace(
        go.Bar(
            x=["Sem IoT", "Com IoT"],
            y=[total_sem_iot, total_com_iot],
            name="Custo"
        )
    )

    grafico_custos.update_layout(
        title="Comparação dos custos operacionais",
        xaxis_title="Cenário",
        yaxis_title="Custo (R$)",
        template="plotly_white"
    )

    grafico_custos_html = pio.to_html(
        grafico_custos,
        full_html=False
    )

    # GRÁFICO DE ECONOMIA POR CATEGORIA

    economia_energia = (
        dados.energia_sem_iot - dados.energia_com_iot
        if dados else 0
    )

    economia_manutencao = (
        dados.manutencao_sem_iot - dados.manutencao_com_iot
        if dados else 0
    )

    economia_paradas = (
        dados.paradas_sem_iot - dados.paradas_com_iot
        if dados else 0
    )

    grafico_economia = go.Figure()

    grafico_economia.add_trace(
        go.Bar(
            x=[
                "Energia",
                "Manutenção",
                "Paradas"
            ],
            y=[
                economia_energia,
                economia_manutencao,
                economia_paradas
            ],
            name="Economia"
        )
    )

    grafico_economia.update_layout(
        title="Economia gerada pelo uso de IoT",
        xaxis_title="Categoria",
        yaxis_title="Economia (R$)",
        template="plotly_white"
    )

    grafico_economia_html = pio.to_html(
        grafico_economia,
        full_html=False
    )

    contexto = {
        "dados": dados,

        "total_sem_iot": round(total_sem_iot, 2),

        "total_com_iot": round(total_com_iot, 2),

        "economia": round(economia, 2),

        "percentual_economia": round(
            percentual_economia,
            2
        ),

        "economia_energia": round(
            economia_energia,
            2
        ),

        "economia_manutencao": round(
            economia_manutencao,
            2
        ),

        "economia_paradas": round(
            economia_paradas,
            2
        ),

        "grafico_custos": grafico_custos_html,

        "grafico_economia": grafico_economia_html,
    }

    return render(
        request,
        "dashboard/index.html",
        contexto
    )