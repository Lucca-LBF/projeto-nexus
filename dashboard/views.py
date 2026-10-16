import math
from django.shortcuts import redirect, render
import plotly.graph_objects as go
import plotly.io as pio

from simulador.segmentos import SEGMENTOS

CHAVE_SESSAO = 'simulacao'
DIAS_POR_MES = 30

COR_SEM_IOT = '#dc2626'
COR_COM_IOT = '#16a34a'
COR_SENSOR = '#2563eb'
COR_REFERENCIA = '#f59e0b'

CONFIG_PLOTLY = {'responsive': True, 'displayModeBar': True}

# rótulos dos gráficos
ROTULOS = {
    'paradas': {
        'eixo_y': 'Custo de falhas (R$)',
        'sem_iot': 'Sem IoT (corretiva)',
        'com_iot': 'Com IoT (preditiva)',
        'titulo': 'custos de falha',
    },
    'perdas': {
        'eixo_y': 'Perdas estimadas (R$)',
        'sem_iot': 'Sem monitoramento',
        'com_iot': 'Com monitoramento IoT',
        'titulo': 'perdas',
    },
}


def _num(valor, casas=2):
    texto = f"{valor:,.{casas}f}"
    return texto.replace(',', 'X').replace('.', ',').replace('X', '.')


def _brl(valor, casas=2):
    sinal = '- ' if valor < 0 else ''
    return f"{sinal}R$ {_num(abs(valor), casas)}"


def _pct(valor, casas=1):
    return f"{_num(valor, casas)}%"


#grafico
def _layout(fig, titulo, eixo_x=None, eixo_y=None, hovermode='x unified'):
    fig.update_layout(
        title=titulo,
        xaxis_title=eixo_x,
        yaxis_title=eixo_y,
        template='plotly_white',
        hovermode=hovermode,
        autosize=True,
        height=420,
        separators=',.',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(l=60, r=20, t=80, b=60),
    )
    fig.update_yaxes(tickprefix='R$ ', tickformat=',.0f')


def _agrupar_por_mes(valores):
    return [sum(valores[i:i + DIAS_POR_MES]) for i in range(0, len(valores), DIAS_POR_MES)]


def _figura_linha(simulacao, rotulos):
    dias = simulacao.get('dados_grafico_dias', [])
    sem_iot = simulacao.get('dados_grafico_sem_iot', [])
    com_iot = simulacao.get('dados_grafico_com_iot', [])

    n = min(len(dias), len(sem_iot), len(com_iot))
    if n == 0:
        return None
    dias, sem_iot, com_iot = dias[:n], sem_iot[:n], com_iot[:n]

    if n <= DIAS_POR_MES:
        eixo_x = [f'Dia {d}' for d in dias]
        unidade = 'diária'
    else:
        sem_iot = _agrupar_por_mes(sem_iot)
        com_iot = _agrupar_por_mes(com_iot)
        eixo_x = [f'Mês {i}' for i in range(1, len(sem_iot) + 1)]
        unidade = 'mensal'

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=eixo_x, y=sem_iot, mode='lines+markers', name=rotulos['sem_iot'],
        line=dict(color=COR_SEM_IOT, width=3), marker=dict(size=6),
    ))
    fig.add_trace(go.Scatter(
        x=eixo_x, y=com_iot, mode='lines+markers', name=rotulos['com_iot'],
        line=dict(color=COR_COM_IOT, width=3), marker=dict(size=6),
    ))
    _layout(fig, f"Projeção {unidade} de {rotulos['titulo']}", 'Período de análise', rotulos['eixo_y'])
    fig.update_yaxes(rangemode='tozero')
    return fig


def _figura_sensibilidade(simulacao, segmento):
    """Resultado líquido para diferentes reduções de perdas.

    A linha é exata: resultado = total_sem_iot * redução - investimento.
    """
    total_sem = simulacao.get('total_sem_iot', 0)
    if total_sem <= 0:
        return None

    economia = simulacao.get('economia_bruta', 0)
    investimento = simulacao.get('investimento_periodo', 0)
    liquido = simulacao.get('resultado_liquido', 0)

    efetiva = economia / total_sem * 100
    referencia = segmento['reducao_iot'] * 100
    equilibrio = investimento / total_sem * 100

    # eixo x de 0% até um limite múltiplo de 5 que mostre o ponto de equilíbrio
    limite = max(35, math.ceil(referencia), math.ceil(efetiva))
    if equilibrio < 100:
        limite = max(limite, math.ceil(equilibrio) + 5)
    limite = min(math.ceil(limite / 5) * 5, 100)

    xs = list(range(0, limite + 1, 5))
    ys = [total_sem * x / 100 - investimento for x in xs]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode='lines', name='Resultado líquido',
        line=dict(color=COR_SENSOR, width=3),
        hovertemplate='Redução de %{x}%<br>Resultado: R$ %{y:,.2f}<extra></extra>',
    ))
    fig.add_trace(go.Scatter(
        x=[efetiva], y=[liquido], mode='markers', name='Sua simulação',
        marker=dict(size=13, color=COR_COM_IOT if liquido >= 0 else COR_SEM_IOT,
                    line=dict(width=2, color='white')),
        hovertemplate=f'Redução efetiva de {_pct(efetiva)}<br>Resultado: {_brl(liquido)}<extra></extra>',
    ))
    fig.add_trace(go.Scatter(
        x=[referencia], y=[total_sem * referencia / 100 - investimento],
        mode='markers', name='Premissa de referência',
        marker=dict(size=12, symbol='diamond', color=COR_REFERENCIA, line=dict(width=2, color='white')),
        hovertemplate=f'Premissa de {_pct(referencia, 0)}<extra></extra>',
    ))

    fig.add_hline(y=0, line_color='#9ca3af', line_width=1)
    if equilibrio <= limite:
        fig.add_vline(
            x=equilibrio, line_dash='dash', line_color='#6b7280',
            annotation_text=f'Equilíbrio: {_pct(equilibrio)}', annotation_position='top left',
        )

    _layout(fig, 'Sensibilidade do resultado líquido',
            'Redução de perdas com IoT', 'Resultado líquido (R$)', hovermode='closest')
    fig.update_xaxes(ticksuffix='%')
    return fig


def _figura_barras(simulacao, rotulos):
    total_sem = simulacao.get('total_sem_iot', 0)
    if total_sem <= 0:
        return None

    nomes = [rotulos['sem_iot'], rotulos['com_iot'], 'Investimento em sensores']
    valores = [total_sem, simulacao.get('total_com_iot', 0), simulacao.get('investimento_periodo', 0)]

    fig = go.Figure(go.Bar(
        x=nomes, y=valores,
        marker_color=[COR_SEM_IOT, COR_COM_IOT, COR_SENSOR],
        text=[_brl(v, 0) for v in valores], textposition='outside', cliponaxis=False,
        hovertemplate='%{x}<br>R$ %{y:,.2f}<extra></extra>',
    ))
    _layout(fig, 'Comparativo do período', None, 'Valor no período (R$)', hovermode='closest')
    fig.update_layout(showlegend=False)
    fig.update_yaxes(rangemode='tozero')
    return fig


def _indicadores(simulacao, segmento):
    total_sem = simulacao.get('total_sem_iot', 0)
    economia = simulacao.get('economia_bruta', 0)
    investimento = simulacao.get('investimento_periodo', 0)
    liquido = simulacao.get('resultado_liquido', 0)
    dias = simulacao.get('tempo_amostra', 30)
    pontos = simulacao.get('num_maquinas', 0)
    custo_sensor = simulacao.get('custo_sensor_iot', 0)
    meses = dias / DIAS_POR_MES

    kpis = []

    kpis.append({
        'titulo': f'Resultado líquido ({dias} dias)',
        'valor': _brl(liquido),
        'detalhe': (f'ROI de {_pct(liquido / investimento * 100)}'
                    if investimento > 0 else 'Sem investimento informado'),
        'classe': 'text-success' if liquido >= 0 else 'text-danger',
    })

    economia_mensal = economia / meses
    kpis.append({
        'titulo': 'Economia evitada por mês',
        'valor': _brl(economia_mensal),
        'detalhe': f'{_brl(economia)} no período',
        'classe': '',
    })

    custo_hora = simulacao.get('custo_hora_parada', 0)
    if segmento['modelo'] == 'paradas' and custo_hora > 0:
        kpis.append({
            'titulo': 'Horas de parada evitadas',
            'valor': f"{_num(economia / custo_hora, 1)} h",
            'detalhe': f'em {dias} dias',
            'classe': '',
        })

    if pontos > 0:
        por_ponto = economia_mensal / pontos
        kpis.append({
            'titulo': 'Economia mensal por ponto',
            'valor': _brl(por_ponto),
            'detalhe': f'Cada sensor custa {_brl(custo_sensor, 0)} por mês',
            'classe': 'text-success' if por_ponto >= custo_sensor else 'text-danger',
        })

    if total_sem > 0:
        kpis.append({
            'titulo': 'Redução efetiva de perdas',
            'valor': _pct(economia / total_sem * 100),
            'detalhe': f"Premissa de referência: {_pct(segmento['reducao_iot'] * 100, 0)}",
            'classe': '',
        })

    return kpis


def _entradas_e_referencias(simulacao, segmento):
    rotulo_pontos, unidade_pontos = segmento['rotulo_pontos']

    entradas = [
        ('Segmento', segmento['nome']),
        (rotulo_pontos, f"{simulacao.get('num_maquinas', 0)} {unidade_pontos}"),
    ]
    if segmento['modelo'] == 'perdas':
        entradas.append(('Perda mensal informada', _brl(simulacao.get('perda_mensal', 0), 0)))
    else:
        entradas.append(('Custo da hora parada', _brl(simulacao.get('custo_hora_parada', 0), 0)))
    entradas.append(('Custo mensal do sensor', _brl(simulacao.get('custo_sensor_iot', 0), 0)))
    entradas.append(('Período simulado', f"{simulacao.get('tempo_amostra', 30)} dias"))

    referencias = [('Redução de perdas com IoT', _pct(segmento['reducao_iot'] * 100, 0))]
    if segmento['modelo'] == 'paradas':
        referencias.append(
            ('Horas de parada por máquina ao dia', f"{_num(segmento['taxa_falha_base'], 2)} h"))

    return entradas, referencias


def dashboard(request):
    simulacao = request.session.get(CHAVE_SESSAO)
    if not simulacao or 'total_sem_iot' not in simulacao:
        return redirect('formulario_simulador')

    segmento = SEGMENTOS.get(simulacao.get('tipo_industria'), SEGMENTOS['padrao'])
    rotulos = ROTULOS[segmento['modelo']]

    entradas, referencias = _entradas_e_referencias(simulacao, segmento)

    # manutenção e energia: estimativas complementares, só no modelo "paradas"
    # e fora do resultado líquido (que considera apenas a redução das perdas)
    complementares = None
    if segmento['modelo'] == 'paradas':
        complementares = [
            ('Economia estimada em manutenção', _brl(simulacao.get('economia_manutencao', 0))),
            ('Economia estimada em energia', _brl(simulacao.get('economia_energia', 0))),
        ]

    # a ordem importa: o primeiro gráfico carrega o plotly.js, os outros reaproveitam
    figuras = {
        'linha': _figura_linha(simulacao, rotulos),
        'sensibilidade': _figura_sensibilidade(simulacao, segmento),
        'barras': _figura_barras(simulacao, rotulos),
    }
    graficos = {}
    incluir_js = True
    for chave, fig in figuras.items():
        if fig is None:
            graficos[chave] = None
            continue
        graficos[chave] = pio.to_html(
            fig, full_html=False,
            include_plotlyjs='cdn' if incluir_js else False,
            config=CONFIG_PLOTLY,
        )
        incluir_js = False

    contexto = {
        'segmento_nome': segmento['nome'],
        'dias': simulacao.get('tempo_amostra', 30),
        'sem_perdas': simulacao.get('total_sem_iot', 0) <= 0,
        'kpis': _indicadores(simulacao, segmento),
        'entradas': entradas,
        'referencias': referencias,
        'premissa_confirmada': segmento.get('premissa_confirmada', True),
        'complementares': complementares,
        'graficos': graficos,
    }
    return render(request, 'dashboard/index.html', contexto)