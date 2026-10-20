"""Relatório completo para baixar em PDF: junta o resultado da simulação e o dashboard.

Reaproveita os cálculos e os gráficos de dashboard/views.py e a simulação de simulador/views.py.
O PDF não é gerado no servidor: a página abre a impressão do navegador ("Salvar como PDF")."""

import plotly.io as pio
from django.shortcuts import redirect, render

from simulador.segmentos import SEGMENTOS
from simulador.views import CHAVE_SESSAO, _calcular

from . import views as dash

ALTURA_GRAFICO = 300
CONFIG_RELATORIO = {'responsive': True, 'displayModeBar': False}


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
        'equilibrio': dash._figura_sensibilidade(salvo, segmento),
    }

    contexto = {
        'nome_industria': resultado['nome_industria'],
        'dias': resultado['dias_simulados'],
        'resumo': resultado['resumo'],
        'feedback': resultado['feedback'],
        'como_calculamos': resultado['como_calculamos'],
        'kpis': dash._indicadores(salvo, segmento),
        'sensores_atuais': resultado['sensores_atuais'],
        'graficos': _html_graficos(figuras),
        'sem_perdas': salvo.get('total_sem_iot', 0) <= 0,
        # sem valor negativo: quando não paga, mostra um texto em vez do número
        'tem_retorno': liquido >= 0,
        'lucro': dash._brl(liquido) if liquido >= 0 else 'Ainda sem retorno',
        'roi': resultado['roi'] if liquido >= 0 else 'Abaixo do equilíbrio',
        'imprimir': request.GET.get('imprimir') == '1',
    }
    return render(request, 'dashboard/relatorio.html', contexto)
