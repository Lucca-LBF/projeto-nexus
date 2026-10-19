"""Relatório completo para baixar em PDF: junta o resultado da simulação e o dashboard.

Reaproveita os cálculos e os gráficos de dashboard/views.py e a simulação de simulador/views.py.
O PDF não é gerado no servidor: a página abre a impressão do navegador ("Salvar como PDF")."""

import math

import plotly.graph_objects as go
import plotly.io as pio
from django.shortcuts import redirect, render

from simulador.segmentos import SEGMENTOS
from simulador.views import CHAVE_SESSAO, _calcular

from . import views as dash

ALTURA_GRAFICO = 300
CONFIG_RELATORIO = {'responsive': True, 'displayModeBar': False}


def _figura_equilibrio(simulacao, segmento):
    """Economia para diferentes reduções de perdas, contra o investimento em sensores.

    Mostra o mesmo ponto de equilíbrio do gráfico de sensibilidade, mas só com valores positivos."""
    total_sem = simulacao.get('total_sem_iot', 0)
    if total_sem <= 0:
        return None

    investimento = simulacao.get('investimento_periodo', 0)
    economia = simulacao.get('economia_bruta', 0)
    efetiva = economia / total_sem * 100
    referencia = segmento['reducao_iot'] * 100
    equilibrio = investimento / total_sem * 100

    limite = max(35, math.ceil(referencia), math.ceil(efetiva))
    if equilibrio < 100:
        limite = max(limite, math.ceil(equilibrio) + 5)
    limite = min(math.ceil(limite / 5) * 5, 100)

    xs = list(range(0, limite + 1, 5))
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xs, y=[total_sem * x / 100 for x in xs], mode='lines', name='Economia estimada',
        line=dict(color=dash.COR_COM_IOT, width=3),
        hovertemplate='Redução de %{x}%<br>Economia: R$ %{y:,.2f}<extra></extra>',
    ))
    fig.add_trace(go.Scatter(
        x=[0, limite], y=[investimento, investimento], mode='lines', name='Investimento em sensores',
        line=dict(color=dash.COR_SENSOR, width=3, dash='dash'), hoverinfo='skip',
    ))
    fig.add_trace(go.Scatter(
        x=[efetiva], y=[economia], mode='markers', name='Sua simulação',
        marker=dict(size=13, color=dash.COR_COM_IOT, line=dict(width=2, color='white')),
        hovertemplate=f'Redução efetiva de {dash._pct(efetiva)}<extra></extra>',
    ))
    fig.add_trace(go.Scatter(
        x=[referencia], y=[total_sem * referencia / 100], mode='markers', name='Premissa de referência',
        marker=dict(size=12, symbol='diamond', color=dash.COR_REFERENCIA, line=dict(width=2, color='white')),
        hovertemplate=f'Premissa de {dash._pct(referencia, 0)}<extra></extra>',
    ))
    if equilibrio <= limite:
        fig.add_vline(x=equilibrio, line_dash='dot', line_color='#6b7280',
                      annotation_text=f'Equilíbrio: {dash._pct(equilibrio)}', annotation_position='top left')

    dash._layout(fig, 'Economia x investimento', 'Redução de perdas com IoT', 'Valor no período (R$)',
                 hovermode='closest')
    fig.update_xaxes(ticksuffix='%')
    fig.update_yaxes(rangemode='tozero')
    return fig


def _html_graficos(figuras):
    """Converte as figuras em HTML; a primeira carrega o plotly.js e as outras reaproveitam."""
    graficos = {}
    incluir_js = True
    for chave, fig in figuras.items():
        if fig is None:
            graficos[chave] = None
            continue
        fig.update_layout(height=ALTURA_GRAFICO, margin=dict(l=60, r=20, t=60, b=50))
        graficos[chave] = pio.to_html(
            fig, full_html=False,
            include_plotlyjs='cdn' if incluir_js else False,
            config=CONFIG_RELATORIO,
        )
        incluir_js = False
    return graficos


def relatorio(request):
    salvo = request.session.get(CHAVE_SESSAO)
    # sem simulação guardada não há o que mostrar: volta ao formulário
    if not salvo or 'num_maquinas' not in salvo:
        return redirect('formulario_simulador')

    # roda de novo a simulação (mesma semente): garante totais e séries atualizados e o texto do resultado
    resultado = _calcular(salvo)
    segmento = SEGMENTOS.get(salvo.get('tipo_industria'), SEGMENTOS['padrao'])
    rotulos = dash.ROTULOS[segmento['modelo']]

    liquido = salvo.get('resultado_liquido', 0)
    figuras = {
        'linha': dash._figura_linha(salvo, rotulos),
        'barras': dash._figura_barras(salvo, rotulos),
        'equilibrio': _figura_equilibrio(salvo, segmento),
    }

    contexto = {
        'nome_industria': resultado['nome_industria'],
        'dias': resultado['dias_simulados'],
        'resumo': resultado['resumo'],
        'feedback': resultado['feedback'],
        'como_calculamos': resultado['como_calculamos'],
        'kpis': dash._indicadores(salvo, segmento),
        'graficos': _html_graficos(figuras),
        'sem_perdas': salvo.get('total_sem_iot', 0) <= 0,
        # sem valor negativo: quando não paga, mostra um texto em vez do número
        'tem_retorno': liquido >= 0,
        'lucro': dash._brl(liquido) if liquido >= 0 else 'Ainda sem retorno',
        'roi': resultado['roi'] if liquido >= 0 else 'Abaixo do equilíbrio',
        'imprimir': request.GET.get('imprimir') == '1',
    }
    return render(request, 'dashboard/relatorio.html', contexto)
