import math
from django.shortcuts import redirect, render
import plotly.graph_objects as go
import plotly.io as pio

from simulador.feedback import faixa_investimento, montar_sensores_atuais
from simulador.segmentos import ACOMPANHAMENTO_RESUMO, SEGMENTOS
from simulador.views import _regime

CHAVE_SESSAO = 'simulacao'
DIAS_POR_MES = 30

COR_SEM_IOT = '#64748b'
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
    """Economia estimada para diferentes reduções de perdas.

    A linha é exata: economia = total_sem_iot * redução. O investimento não é desenhado:
    só o ponto de equilíbrio (a redução mínima para os sensores se pagarem) aparece como uma marca."""
    total_sem = simulacao.get('total_sem_iot', 0)
    if total_sem <= 0:
        return None

    economia = simulacao.get('economia_bruta', 0)
    investimento = simulacao.get('investimento_periodo', 0)

    efetiva = economia / total_sem * 100
    referencia = segmento['reducao_iot'] * 100
    equilibrio = investimento / total_sem * 100

    # eixo x de 0% até um limite múltiplo de 5 que mostre o ponto de equilíbrio
    limite = max(35, math.ceil(referencia), math.ceil(efetiva))
    if equilibrio < 100:
        limite = max(limite, math.ceil(equilibrio) + 5)
    limite = min(math.ceil(limite / 5) * 5, 100)

    xs = list(range(0, limite + 1, 5))
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xs, y=[total_sem * x / 100 for x in xs], mode='lines', name='Economia estimada',
        line=dict(color=COR_COM_IOT, width=3),
        hovertemplate='Redução de %{x}%<br>Economia: R$ %{y:,.2f}<extra></extra>',
    ))
    fig.add_trace(go.Scatter(
        x=[efetiva], y=[economia], mode='markers', name='Sua simulação',
        marker=dict(size=13, color=COR_COM_IOT, line=dict(width=2, color='white')),
        hovertemplate=f'Redução efetiva de {_pct(efetiva)}<br>Economia: {_brl(economia)}<extra></extra>',
    ))
    fig.add_trace(go.Scatter(
        x=[referencia], y=[total_sem * referencia / 100], mode='markers', name='Premissa de referência',
        marker=dict(size=12, symbol='diamond', color=COR_REFERENCIA, line=dict(width=2, color='white')),
        hovertemplate=f'Premissa de {_pct(referencia, 0)}<extra></extra>',
    ))
    if equilibrio <= limite:
        fig.add_vline(
            x=equilibrio, line_dash='dash', line_color='#6b7280',
            annotation_text=f'Equilíbrio: {_pct(equilibrio)}', annotation_position='top left',
        )

    _layout(fig, 'Economia estimada por redução de perdas',
            'Redução de perdas com IoT', 'Economia no período (R$)', hovermode='closest')
    fig.update_xaxes(ticksuffix='%')
    fig.update_yaxes(rangemode='tozero')
    return fig


def _figura_barras(simulacao, rotulos):
    total_sem = simulacao.get('total_sem_iot', 0)
    if total_sem <= 0:
        return None

    nomes = [rotulos['sem_iot'], rotulos['com_iot']]
    valores = [total_sem, simulacao.get('total_com_iot', 0)]

    fig = go.Figure(go.Bar(
        x=nomes, y=valores,
        marker_color=[COR_SEM_IOT, COR_COM_IOT],
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
    # só os pontos que ainda não têm sensor entram no investimento
    pontos = simulacao.get('pontos_novos', simulacao.get('num_maquinas', 0))
    meses = dias / DIAS_POR_MES

    kpis = []

    if liquido >= 0:
        kpis.append({
            'titulo': f'Resultado líquido ({dias} dias)',
            'valor': _brl(liquido),
            'detalhe': (f'ROI de {_pct(liquido / investimento * 100)}'
                        if investimento > 0 else 'Sem investimento informado'),
            'classe': 'text-success',
        })
    else:
        # sem valor negativo nem vermelho: mostra a economia possível e o que falta para os sensores se pagarem
        kpis.append({
            'titulo': f'Potencial de economia ({dias} dias)',
            'valor': _brl(economia),
            'detalhe': 'Estimativa. Pelo valor central do investimento, ainda não cobre os sensores.',
            'classe': 'text-info',
        })
        if total_sem > 0 and investimento > 0:
            equilibrio = investimento / total_sem * 100
            kpis.append({
                'titulo': 'Para os sensores se pagarem',
                'valor': f'{_pct(equilibrio, 0)} de redução' if equilibrio < 100 else 'Revisar valores',
                'detalhe': (f"Referência do setor: {_pct(segmento['reducao_iot'] * 100, 0)} de redução de perdas"
                            if equilibrio < 100 else 'A perda informada é menor que o investimento estimado'),
                'classe': 'text-info',
            })
        investimento_min = simulacao.get('investimento_min', 0)
        if economia > investimento_min > 0:
            kpis.append({
                'titulo': 'Se o investimento ficar no mínimo da faixa',
                'valor': _brl(economia - investimento_min),
                'detalhe': 'Lucro estimado no período. Uma cotação real pode mudar o resultado.',
                'classe': 'text-success',
            })

    if simulacao.get('investimento_max', 0) > 0:
        kpis.append({
            'titulo': 'Investimento estimado',
            'valor': faixa_investimento(simulacao['investimento_min'], simulacao['investimento_max'], curta=True),
            'detalhe': 'Só sensores, estimativa de mercado para o seu setor (não é preço da Bzu)',
            'classe': '',
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
        # só a parte das paradas: a economia com conserto de emergência fica de fora
        economia_paradas = simulacao.get('economia_paradas', economia)
        kpis.append({
            'titulo': 'Horas de parada evitadas',
            'valor': f"{_num(economia_paradas / custo_hora, 1)} h",
            'detalhe': f'em {dias} dias',
            'classe': '',
        })

    if pontos > 0:
        por_ponto = economia_mensal / pontos
        kpis.append({
            'titulo': 'Economia mensal por ponto',
            'valor': _brl(por_ponto),
            'detalhe': 'Média por ponto que ainda será monitorado',
            'classe': 'text-success' if por_ponto >= segmento['custo_ponto'] else 'text-info',
        })

    if simulacao.get('cobertura', 0) > 0:
        kpis.append({
            'titulo': 'Já evitado com seus sensores',
            'valor': _brl(simulacao.get('economia_ja_aproveitada', 0)),
            'detalhe': f"em {dias} dias, com sensores em cerca de {round(simulacao['cobertura'] * 100)}% dos pontos",
            'classe': 'text-success',
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
    fator_regime, texto_regime = _regime(simulacao.get('regime_funcionamento'))

    entradas = [
        ('Segmento', segmento['nome']),
        (rotulo_pontos, f"{simulacao.get('num_maquinas', 0)} {unidade_pontos}"),
    ]
    if segmento['modelo'] == 'perdas':
        entradas.append(('Perda mensal informada', _brl(simulacao.get('perda_mensal', 0), 0)))
    else:
        # o regime só existe (e só muda a conta) nos segmentos de paradas
        if texto_regime:
            entradas.append(('Funcionamento', texto_regime))
        entradas.append(('Custo da hora parada', _brl(simulacao.get('custo_hora_parada', 0), 0)))
    entradas.append(('Sensores atuais', ACOMPANHAMENTO_RESUMO.get(simulacao.get('acompanhamento_atual'), 'Não informado')))

    # opcional: só aparece se o usuário preencheu
    conserto = simulacao.get('conserto_mensal', 0)
    if conserto > 0:
        entradas.append(('Conserto de emergência', f"{_brl(conserto, 0)} por mês"))

    entradas.append(('Período simulado', f"{simulacao.get('tempo_amostra', 30)} dias"))

    referencias = [('Redução de perdas com IoT', _pct(segmento['reducao_iot'] * 100, 0))]
    if segmento['modelo'] == 'paradas':
        # a taxa base já multiplicada pelo regime de funcionamento, como no cálculo
        referencias.append(
            ('Horas de parada por máquina ao dia',
             f"{_num(segmento['taxa_falha_base'] * fator_regime, 2)} h"))

    return entradas, referencias


def dashboard(request):
    simulacao = request.session.get(CHAVE_SESSAO)
    if not simulacao or 'total_sem_iot' not in simulacao:
        return redirect('formulario_simulador')

    segmento = SEGMENTOS.get(simulacao.get('tipo_industria'), SEGMENTOS['padrao'])
    rotulos = ROTULOS[segmento['modelo']]

    entradas, referencias = _entradas_e_referencias(simulacao, segmento)

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
        'graficos': graficos,
        'sensores_atuais': montar_sensores_atuais(
            simulacao.get('cobertura', 0), simulacao.get('economia_ja_aproveitada', 0),
            simulacao.get('economia_bruta', 0), simulacao.get('economia_potencial_total', 0),
            simulacao.get('tempo_amostra', 30)),
    }
    return render(request, 'dashboard/index.html', contexto)