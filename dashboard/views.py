from django.shortcuts import redirect, render
from simulador.segmentos import SEGMENTOS
import plotly.graph_objects as go
import plotly.io as pio

CHAVE_SESSAO = 'simulacao'
DIAS_POR_MES = 30


def _agrupar_por_mes(valores):
    return [
        sum(valores[i:i + DIAS_POR_MES])
        for i in range(0, len(valores), DIAS_POR_MES)
    ]

def _montar_entradas(simulacao):
    segmento = SEGMENTOS.get(simulacao.get('tipo_industria'), SEGMENTOS['padrao'])
    rotulo_pontos, unidade_pontos = segmento['rotulo_pontos']

    entradas = [
        ('Segmento', segmento['nome']),
        (rotulo_pontos, f"{simulacao.get('num_maquinas', 0)} {unidade_pontos}"),
    ]

    if segmento['modelo'] == 'perdas':
        entradas.append(('Perda mensal estimada', f"R$ {simulacao.get('perda_mensal', 0)}"))
    else:
        entradas.append(('Custo da hora parada', f"R$ {simulacao.get('custo_hora_parada', 0)}"))

    entradas.append(('Custo mensal do sensor', f"R$ {simulacao.get('custo_sensor_iot', 0)}"))
    entradas.append(('Período simulado', f"{simulacao.get('tempo_amostra', 30)} dias"))
    return entradas

def _montar_grafico(dias, sem_iot, com_iot):
    n = min(len(dias), len(sem_iot), len(com_iot))
    if n == 0:
        return None

    dias, sem_iot, com_iot = dias[:n], sem_iot[:n], com_iot[:n]

    if n <= DIAS_POR_MES:
        eixo_x = [f'Dia {d}' for d in dias]
        unidade = 'Diária'
    else:
        sem_iot = _agrupar_por_mes(sem_iot)
        com_iot = _agrupar_por_mes(com_iot)
        eixo_x = [f'Mês {i}' for i in range(1, len(sem_iot) + 1)]
        unidade = 'Mensal'

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=eixo_x, y=sem_iot, mode='lines+markers',
        name='Sem IoT (Corretiva)',
        line=dict(color='#dc2626', width=3), marker=dict(size=6),
    ))
    fig.add_trace(go.Scatter(
        x=eixo_x, y=com_iot, mode='lines+markers',
        name='Com IoT (Preditiva)',
        line=dict(color='#81358D', width=3), marker=dict(size=6),
    ))

    fig.update_layout(
        title=f'Projeção {unidade} dos Custos de Falha',
        xaxis_title='Período de Análise',
        yaxis_title='Custo de Falhas (R$)',
        template='plotly_white',
        hovermode='x unified',
        autosize=True,
        separators=',.',
        legend=dict(orientation='h', yanchor='bottom', y=1.02,
                    xanchor='right', x=1),
        margin=dict(l=60, r=20, t=80, b=60),
    )
    fig.update_yaxes(tickprefix='R$ ', tickformat=',.2f', rangemode='tozero')

    return pio.to_html(
        fig,
        full_html=False,
        include_plotlyjs='cdn',
        config={'responsive': True, 'displayModeBar': True},
    )


def dashboard(request):
    simulacao = request.session.get(CHAVE_SESSAO)

    if not simulacao:
        return redirect('formulario_simulador')  # ou 'simulador:formulario_simulador'

    total_sem_iot = simulacao.get('total_sem_iot', 0)
    economia = simulacao.get('resultado_liquido', 0)
    percentual = economia / total_sem_iot * 100 if total_sem_iot > 0 else 0
    contexto = {
        'entradas': _montar_entradas(simulacao),
        'total_sem_iot': total_sem_iot,
        'total_com_iot': simulacao.get('total_com_iot', 0),
        'economia': economia,
        'economia_paradas': simulacao.get('economia_paradas', 0),
        'economia_manutencao': simulacao.get('economia_manutencao', 0),
        'economia_energia': simulacao.get('economia_energia', 0),
        'percentual_economia': percentual,
        'grafico_linhas': _montar_grafico(
            simulacao.get('dados_grafico_dias', []),
            simulacao.get('dados_grafico_sem_iot', []),
            simulacao.get('dados_grafico_com_iot', []),
        ),
    }
    return render(request, 'dashboard/index.html', contexto)