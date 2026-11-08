import math
from django.shortcuts import redirect, render
import plotly.graph_objects as go

from simulador.feedback import (faixa_investimento, moeda_estimada, moeda_inteira, montar_sensores_atuais,
                                NIVEL_EVIDENCIA)
from simulador.segmentos import ACOMPANHAMENTO_RESUMO, SEGMENTOS
from simulador.views import _calcular, _regime

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


# escalas do gráfico de linha: (dias por bloco, nome do bloco, unidade no título)
ESCALAS = [(1, 'Dia', 'diária'), (7, 'Semana', 'semanal'), (15, 'Quinzena', 'quinzenal'), (30, 'Mês', 'mensal')]


def escala_padrao(n):
    """Escala inicial do gráfico pelo tamanho do período (a mesma regra da tela de resultado)."""
    if n >= 360:
        return 30
    if n >= 180:
        return 15
    if n >= 120:
        return 7
    return 1


def _blocos(n, tamanho_bloco):
    """Intervalos de dias de cada bloco do gráfico: [(início, fim), ...].

    Quando sobram poucos dias no fim (menos da metade de um bloco), eles entram no bloco anterior, para o
    gráfico não terminar numa queda falsa; quando sobram mais, viram um bloco parcial. Nunca se multiplica
    nada: o total do gráfico é sempre o total do período."""
    blocos = [(i, min(i + tamanho_bloco, n)) for i in range(0, n, tamanho_bloco)]
    sobra = n % tamanho_bloco
    if tamanho_bloco > 1 and sobra and len(blocos) > 1 and sobra < tamanho_bloco / 2:
        inicio = blocos[-2][0]
        blocos = blocos[:-2] + [(inicio, n)]
    return blocos


def _agrupar(valores, tamanho_bloco):
    """Soma os valores em blocos (veja _blocos)."""
    return [sum(valores[a:b]) for a, b in _blocos(len(valores), tamanho_bloco)]


def _rotulos_blocos(n, tamanho_bloco, nome):
    """'Semana 1', 'Semana 2', ... com o último marcado quando não tem o tamanho normal."""
    rotulos = []
    for i, (a, b) in enumerate(_blocos(n, tamanho_bloco), start=1):
        dias = b - a
        rotulo = f'{nome} {i}'
        if tamanho_bloco > 1 and dias != tamanho_bloco:
            rotulo += f' ({dias} dias)' if dias > tamanho_bloco else f' (parcial, {dias} dia{"s" if dias > 1 else ""})'
        rotulos.append(rotulo)
    return rotulos


def _figura_linha(simulacao, rotulos, com_menu=True):
    """Custos com e sem IoT ao longo do período. Com menu, dá para trocar a escala (dia, semana, quinzena, mês)
    a partir de 90 dias, como na tela de resultado."""
    dias = simulacao.get('dados_grafico_dias', [])
    sem_iot = simulacao.get('dados_grafico_sem_iot', [])
    com_iot = simulacao.get('dados_grafico_com_iot', [])

    n = min(len(dias), len(sem_iot), len(com_iot))
    if n == 0:
        return None
    sem_iot, com_iot = sem_iot[:n], com_iot[:n]

    padrao = escala_padrao(n)
    escalas = ESCALAS if (com_menu and n >= 90) else [e for e in ESCALAS if e[0] == padrao]

    fig = go.Figure()
    botoes = []
    for indice, (bloco, nome, unidade) in enumerate(escalas):
        eixo_x = _rotulos_blocos(n, bloco, nome)
        visivel = bloco == padrao
        fig.add_trace(go.Scatter(
            x=eixo_x, y=_agrupar(sem_iot, bloco), mode='lines+markers', name=rotulos['sem_iot'],
            line=dict(color=COR_SEM_IOT, width=3), marker=dict(size=6), visible=visivel,
        ))
        fig.add_trace(go.Scatter(
            x=eixo_x, y=_agrupar(com_iot, bloco), mode='lines+markers', name=rotulos['com_iot'],
            line=dict(color=COR_COM_IOT, width=3), marker=dict(size=6), visible=visivel,
        ))
        mascara = [False] * (2 * len(escalas))
        mascara[2 * indice] = mascara[2 * indice + 1] = True
        botoes.append(dict(label=nome, method='update',
                           args=[{'visible': mascara}, {'title.text': f"Projeção {unidade} de {rotulos['titulo']}"}]))

    unidade_padrao = next(u for b, _, u in escalas if b == padrao)
    _layout(fig, f"Projeção {unidade_padrao} de {rotulos['titulo']}", 'Período de análise', rotulos['eixo_y'])
    fig.update_yaxes(rangemode='tozero')
    if len(escalas) > 1:
        fig.update_layout(updatemenus=[dict(
            type='buttons', direction='right', buttons=botoes, showactive=True,
            active=[b for b, _, _ in escalas].index(padrao),
            x=0, xanchor='left', y=1.02, yanchor='bottom', pad=dict(r=4, t=0),
            bgcolor='#ffffff', bordercolor='#d1d5db', font=dict(size=12),
        )])
        fig.update_layout(margin=dict(t=110), title=dict(y=0.97, yanchor='top'))
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
    # faixa de redução encontrada nos estudos do setor (veja "Fontes dos números")
    ref = segmento.get('reducao_ref')
    if ref:
        minimo, maximo = ref['faixa']
        fig.add_vrect(
            x0=minimo, x1=min(maximo, limite), fillcolor=COR_REFERENCIA, opacity=0.10, line_width=0,
            annotation_text='Faixa dos estudos', annotation_position='bottom right',
            annotation_font=dict(size=11, color='#92400e'),
        )
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
    """Por mês: a economia evitada (separada por origem) ao lado do custo dos sensores.

    Substitui o comparativo de totais do período, que repetia os números dos cards."""
    custo = simulacao.get('custo_mensal', 0)
    economia = simulacao.get('economia_mensal', 0)
    if custo <= 0 or simulacao.get('total_sem_iot', 0) <= 0:
        return None

    meses = simulacao.get('tempo_amostra', 30) / DIAS_POR_MES
    conserto = simulacao.get('economia_conserto_nova', 0) / meses if meses > 0 else 0
    principal = max(economia - conserto, 0)
    nome_principal = 'Paradas evitadas' if rotulos is ROTULOS['paradas'] else 'Perdas evitadas'
    colunas = ['Economia por mês', 'Custo dos sensores por mês']

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=colunas[:1], y=[principal], name=nome_principal, marker_color=COR_COM_IOT,
        hovertemplate=nome_principal + ': R$ %{y:,.2f}<extra></extra>',
    ))
    if conserto > 0:
        fig.add_trace(go.Bar(
            x=colunas[:1], y=[conserto], name='Conserto de emergência evitado', marker_color='#86efac',
            hovertemplate='Conserto evitado: R$ %{y:,.2f}<extra></extra>',
        ))
    minimo, maximo = simulacao.get('custo_mensal_min', custo), simulacao.get('custo_mensal_max', custo)
    fig.add_trace(go.Bar(
        x=colunas[1:], y=[custo], name='Custo dos sensores (valor central)', marker_color=COR_SEM_IOT,
        error_y=dict(type='data', symmetric=False, array=[maximo - custo], arrayminus=[custo - minimo],
                     color='#334155', thickness=1.5, width=10),
        hovertemplate=(f'Custo central: R$ %{{y:,.2f}}<br>Faixa: {_brl(minimo, 0)} a {_brl(maximo, 0)}'
                       '<extra></extra>'),
    ))
    _layout(fig, 'Economia e custo dos sensores por mês', None, 'R$ por mês', hovermode='closest')
    fig.update_layout(barmode='stack', legend=dict(orientation='h', yanchor='top', y=-0.12, xanchor='left', x=0),
                      margin=dict(b=110))
    # o valor de cada coluna escrito em cima, para ler mesmo quando uma barra é muito menor que a outra
    for coluna, valor, topo in ((colunas[0], economia, economia), (colunas[1], custo, maximo)):
        fig.add_annotation(x=coluna, y=topo, text=_brl(valor, 2 if valor < 1000 else 0), showarrow=False,
                           yshift=12, font=dict(size=12, color='#111827'))
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
            'detalhe': (f'ROI estimado de {_pct(liquido / investimento * 100)}'
                        if investimento > 0 else 'Sem investimento informado'),
            'classe': 'text-success',
        })
    else:
        # sem valor negativo nem vermelho: mostra a economia possível e o que falta para os sensores se pagarem
        kpis.append({
            'titulo': f'Potencial de economia ({dias} dias)',
            'valor': _brl(economia),
            'detalhe': (f'Estimativa. Já cobre {_pct_curto(economia / investimento * 100)} do custo dos sensores.'
                        if investimento > 0 else 'Estimativa'),
            'classe': 'text-info',
        })
        if total_sem > 0 and investimento > 0:
            equilibrio = investimento / total_sem * 100
            if equilibrio < 100:
                valor_eq = f'{_pct(equilibrio, 0)} de redução'
                detalhe_eq = f"Referência do setor: {_pct(segmento['reducao_iot'] * 100, 0)} de redução de perdas"
            else:
                # nem 100% de redução pagaria: mostra quanto a hora parada (ou a perda mensal) teria que valer
                alvo = simulacao.get('valor_equilibrio', 0)
                informado = simulacao.get('valor_informado', 0)
                if segmento['modelo'] == 'paradas':
                    rotulo_eq, sufixo_eq = 'Hora parada de', ''
                else:
                    rotulo_eq, sufixo_eq = 'Perda de', ' por mês'
                valor_eq = f'{rotulo_eq} {moeda_inteira(alvo)}{sufixo_eq}' if alvo > 0 else 'Começar por poucos pontos'
                detalhe_eq = (f'Você informou {moeda_inteira(informado)}{sufixo_eq}. '
                              'Vale começar pelos pontos críticos.' if alvo > 0 else 'Onde a perda é maior')
            kpis.append({
                'titulo': 'Para os sensores se pagarem',
                'valor': valor_eq,
                'detalhe': detalhe_eq,
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
            'detalhe': 'Só sensores, estimativa de mercado para o seu setor. O valor final vem na proposta da Bzu.',
            'classe': '',
        })

    economia_mensal = economia / meses
    kpis.append({
        'titulo': 'Economia evitada por mês',
        'valor': _brl(economia_mensal),
        'detalhe': f'{_brl(economia)} no período',
        'classe': '',
    })

    # o custo dos sensores é mensal: o saldo de cada mês diz se compensa (sem número negativo)
    custo_mensal = simulacao.get('custo_mensal', investimento / meses if meses else 0)
    if custo_mensal > 0:
        saldo = economia_mensal - custo_mensal
        kpis.append({
            'titulo': 'Sobra por mês' if saldo >= 0 else 'Para cobrir 100%',
            'valor': _brl(saldo) if saldo >= 0 else f'+ {_brl(-saldo)}',
            'detalhe': (f'Depois de pagar os sensores ({_brl(custo_mensal)} por mês)' if saldo >= 0
                        else f'De economia por mês para cobrir os sensores ({_brl(custo_mensal)} por mês)'),
            'classe': 'text-success' if saldo >= 0 else 'text-info',
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
            'detalhe': f"Custo dos sensores: {_brl(segmento['custo_ponto'], 0)} por ponto por mês",
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


# ---------------------------------------------------------------------------------------------
# Painel do dashboard: veredito, quatro números, mês a mês, cenários e régua do equilíbrio.
# Tudo em texto positivo e sem número negativo; os valores vêm da própria simulação.
# ---------------------------------------------------------------------------------------------

ALTURA_GRAFICO = 220  # px


def _pct_curto(valor):
    """9.6 -> '9,6%'; 44.7 -> '45%'; 0.2 -> '0,2%'."""
    return f"{_num(valor, 1 if valor < 10 else 0)}%"


def _moeda_curta(valor):
    """Valor arredondado sem centavos a partir de R$ 100 (abaixo disso mostra os centavos)."""
    return moeda_inteira(valor) if abs(valor) >= 100 else moeda_estimada(valor)


def _css(valor):
    """Número para CSS com ponto decimal: o template localizado escreveria '30,0', que o navegador ignora."""
    return f"{valor:.1f}"


def _moeda_eixo(valor):
    """Rótulo curto do eixo: 'R$ 18 mil' ou 'R$ 4.500'."""
    if valor >= 10_000:
        return f"R$ {_num(valor / 1000, 0 if valor % 1000 == 0 else 1)} mil"
    return f"R$ {_num(valor, 0 if valor >= 10 else 2)}"


def _grafico_periodos(simulacao):
    """Economia de cada mês (ou semana, em simulações curtas) com a marca do custo dos sensores no mesmo período."""
    sem = simulacao.get('dados_grafico_sem_iot', [])
    com = simulacao.get('dados_grafico_com_iot', [])
    n = min(len(sem), len(com))
    custo_dia = simulacao.get('custo_mensal', 0) / DIAS_POR_MES
    if n == 0 or custo_dia <= 0:
        return None
    bloco, nome = (DIAS_POR_MES, 'Mês') if n > 60 else (7, 'Semana')
    rotulos = _rotulos_blocos(n, bloco, nome)
    economias = [sum(sem[a:b]) - sum(com[a:b]) for a, b in _blocos(n, bloco)]
    custos = [custo_dia * (b - a) for a, b in _blocos(n, bloco)]
    # eixo com valores redondos: três degraus iguais (por exemplo R$ 8 mil, R$ 16 mil, R$ 24 mil)
    maior = max(max(economias), max(custos)) * 1.08 or 1
    degrau_bruto = maior / 3
    potencia = 10 ** math.floor(math.log10(degrau_bruto))
    degrau = next(m * potencia for m in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10) if m * potencia >= degrau_bruto)
    escala = degrau * 3
    itens = []
    for rotulo, economia, custo in zip(rotulos, economias, custos):
        itens.append({
            'rotulo': rotulo,
            'altura': max(round(max(economia, 0) / escala * ALTURA_GRAFICO), 2),
            'marca': round(custo / escala * ALTURA_GRAFICO),
            'descricao': f"{rotulo}: economia de {moeda_estimada(max(economia, 0))}, custo dos sensores de {moeda_estimada(custo)}",
        })
    cobre_todos = all(e >= c for e, c in zip(economias, custos))
    periodo = 'mês' if bloco == DIAS_POR_MES else 'semana'
    if cobre_todos:
        legenda = "Em todos os períodos a economia passa da marca do custo dos sensores."
    else:
        legenda = "Cada barra é a economia do período. A marca tracejada é a meta: o custo dos sensores no mesmo período."
    return {
        'titulo': f"{'Mês a mês' if bloco == DIAS_POR_MES else 'Semana a semana'}: economia e custo dos sensores",
        'itens': itens,
        'colunas': len(itens),
        'eixo': [_moeda_eixo(degrau * k) for k in (3, 2, 1)] + ['R$ 0'],
        'altura': ALTURA_GRAFICO,
        'legenda_custo': (f"Custo dos sensores por {periodo}" if cobre_todos else f"Meta: custo dos sensores por {periodo}"),
        'legenda': legenda,
    }


def _cenarios(simulacao, segmento):
    """Três cenários pela faixa de redução dos estudos: cauteloso, premissa do simulador e otimista."""
    ref = segmento.get('reducao_ref')
    reducao = segmento['reducao_iot']
    economia = simulacao.get('economia_mensal', 0)
    custo = simulacao.get('custo_mensal', 0)
    if not ref or reducao <= 0 or economia <= 0 or custo <= 0:
        return None
    minimo, maximo = ref['faixa']
    premissa = round(reducao * 100)
    base = [('Cauteloso', minimo, f'{minimo}% de redução', 'O menor valor encontrado nos estudos', False),
            ('Premissa do simulador', premissa, f'{premissa}%', 'O valor usado no resultado', True),
            ('Otimista', maximo, f'{maximo}% de redução', 'O maior valor encontrado nos estudos', False)]
    # a economia cresce na mesma proporção da redução (mesma conta da faixa de economia)
    economias = [economia * pct / 100 / reducao for _, pct, _, _, _ in base]
    escala = max(max(economias), custo)
    cenarios = []
    for (nome, pct, rotulo_pct, descricao, destaque), valor_economia in zip(base, economias):
        saldo = valor_economia - custo
        cenarios.append({
            'nome': nome, 'pct': rotulo_pct, 'descricao': descricao, 'destaque': destaque,
            'rotulo': 'Sobra por mês' if saldo >= 0 else 'Cobre do custo',
            'valor': _moeda_curta(saldo) if saldo >= 0 else _pct_curto(valor_economia / custo * 100),
            'economia': _moeda_curta(valor_economia),
            'largura_economia': round(valor_economia / escala * 100),
            'largura_custo': round(custo / escala * 100),
        })
    return {'lista': cenarios, 'custo': _moeda_curta(custo)}


def _regua(simulacao, segmento):
    """Régua de 0% a 50% (ou 100%): faixa dos estudos, valor do simulador e ponto em que a economia cobre o custo."""
    ref = segmento.get('reducao_ref')
    if not ref or simulacao.get('total_sem_iot', 0) <= 0:
        return None
    minimo, maximo = ref['faixa']
    premissa = round(segmento['reducao_iot'] * 100)
    equilibrio = simulacao.get('equilibrio_pct', 0)
    no_alcance = 0 < equilibrio < 100
    limite = 50 if max(maximo, premissa, equilibrio if no_alcance else 0) <= 45 else 100
    passo = limite // 5

    def pos(valor):
        return min(valor, limite) / limite * 100

    nivel = NIVEL_EVIDENCIA.get(ref['confianca'], ref['confianca'])
    if no_alcance:
        texto = (f"A economia cobre o custo a partir de {_pct_curto(equilibrio)} de redução das perdas. "
                 f"Os estudos do setor indicam de {minimo}% a {maximo}% ({nivel}).")
        if equilibrio > premissa:
            texto += " O diagnóstico mede o potencial real da sua operação."
    else:
        alvo = simulacao.get('valor_equilibrio', 0)
        if alvo > 0:
            grandeza = 'cada hora parada custa' if segmento['modelo'] == 'paradas' else 'a perda mensal é de'
            texto = (f"Com os valores informados, a economia cobre o custo quando {grandeza} cerca de "
                     f"{moeda_inteira(alvo)}. Os estudos do setor indicam de {minimo}% a {maximo}% de redução ({nivel}).")
        else:
            texto = (f"Os estudos do setor indicam de {minimo}% a {maximo}% de redução ({nivel}). "
                     "Vale começar pelos pontos críticos, onde a perda é maior.")
    return {
        'texto': texto,
        'faixa_inicio': _css(pos(minimo)), 'faixa_largura': _css(pos(maximo) - pos(minimo)),
        'premissa': _css(pos(premissa)), 'premissa_rotulo': f'{premissa}%',
        'equilibrio': _css(pos(equilibrio)) if no_alcance else None,
        'equilibrio_rotulo': f'Cobre o custo: {_pct_curto(equilibrio)}' if no_alcance else '',
        'faixa_rotulo': f'{minimo}% a {maximo}%',
        'marcas': [f'{v}%' for v in range(0, limite + 1, passo)],
    }


def _caminhos(simulacao, segmento):
    """Quando a economia ainda está abaixo do custo: o que leva a cobrir 100%."""
    economia = simulacao.get('economia_mensal', 0)
    custo_min = simulacao.get('custo_mensal_min', 0)
    equilibrio = simulacao.get('equilibrio_pct', 0)
    ref = segmento.get('reducao_ref') or {'faixa': (0, 0)}
    minimo, maximo = ref['faixa']
    caminhos = []
    if 0 < equilibrio < 100:
        caminhos.append({
            'titulo': 'Redução de perdas que cobre o custo', 'valor': _pct_curto(equilibrio),
            'texto': f'Os estudos do setor indicam de {minimo}% a {maximo}%. O diagnóstico mede o potencial real da sua operação.',
        })
    elif simulacao.get('valor_equilibrio', 0) > 0:
        rotulo = 'Valor da hora parada que cobre o custo' if segmento['modelo'] == 'paradas' else 'Perda mensal que cobre o custo'
        caminhos.append({
            'titulo': rotulo, 'valor': moeda_inteira(simulacao['valor_equilibrio']),
            'texto': f"Você informou {moeda_inteira(simulacao.get('valor_informado', 0))}. O diagnóstico confirma o custo real.",
        })
    if custo_min > 0 and economia > 0:
        if economia >= custo_min:
            texto = f'A economia passa a cobrir o custo, com sobra de cerca de {moeda_estimada(economia - custo_min)} por mês.'
        else:
            texto = f'A economia passa a cobrir {_pct_curto(economia / custo_min * 100)} do custo.'
        caminhos.append({'titulo': 'Com o custo no mínimo da faixa', 'valor': f'{moeda_inteira(custo_min)}/mês',
                         'texto': texto + ' Uma cotação real confirma esse valor.'})
    caminhos.append({'titulo': 'Caminho mais realista', 'valor': 'Piloto nos pontos com maior perda',
                     'texto': 'O diagnóstico mostra onde a perda se concentra e por quais pontos começar.',
                     'destaque': True})
    return caminhos


def _painel(simulacao, segmento):
    """Veredito, os quatro números e os detalhes do topo do dashboard."""
    dias = simulacao.get('tempo_amostra', 30)
    meses = dias / DIAS_POR_MES
    unidade_pontos = segmento['rotulo_pontos'][1]
    meta = f"{segmento['nome']} · {simulacao.get('num_maquinas', 0)} {unidade_pontos.lower()} · {dias} dias"
    total_sem = simulacao.get('total_sem_iot', 0)
    economia = simulacao.get('economia_mensal', 0)
    custo = simulacao.get('custo_mensal', 0)
    if total_sem <= 0 or custo <= 0:
        return {'meta': meta, 'sem_perdas': True,
                'titulo': 'Informe a perda mensal ou o custo da hora parada para ver a sua economia.',
                'sub': 'Com esse valor, o simulador calcula a economia e o custo dos sensores mês a mês.'}

    saldo = economia - custo
    cobre = saldo >= 0
    conserto = simulacao.get('economia_conserto_nova', 0) / meses if meses > 0 else 0
    principal = 'Paradas evitadas' if segmento['modelo'] == 'paradas' else 'Perdas evitadas'
    origem = (f"{principal} {moeda_estimada(max(economia - conserto, 0))} · Conserto {moeda_estimada(conserto)}"
              if conserto > 0 else principal)
    investimento = simulacao.get('investimento_periodo', 0)
    economia_periodo = simulacao.get('economia_bruta', 0)

    if cobre:
        vezes = economia / custo
        roi = simulacao.get('resultado_liquido', 0) / investimento * 100 if investimento > 0 else 0
        titulo = f"Os sensores se pagam e sobram cerca de {moeda_inteira(saldo)} por mês."
        sub = f"A economia estimada é {_num(vezes, 1)} vezes o custo dos sensores. ROI de {_num(roi, 0)}% no período."
    else:
        cobertura = economia / custo * 100
        titulo = f"A economia já cobre {_pct_curto(cobertura)} do custo dos sensores. Veja como chegar a 100%."
        sub = f"O monitoramento evita cerca de {moeda_estimada(economia_periodo)} em perdas no período."

    detalhes = []
    custo_hora = simulacao.get('custo_hora_parada', 0)
    if segmento['modelo'] == 'paradas' and custo_hora > 0:
        horas = simulacao.get('economia_paradas', economia_periodo) / custo_hora
        detalhes.append({'titulo': 'Horas de parada evitadas', 'valor': f"{_num(horas, 1)} h", 'nota': f'em {dias} dias'})
    else:
        ref = segmento.get('reducao_ref')
        nota = f"Faixa dos estudos do setor: {ref['faixa'][0]}% a {ref['faixa'][1]}%" if ref else 'Premissa do simulador'
        detalhes.append({'titulo': 'Redução de perdas usada', 'valor': f"{round(segmento['reducao_iot'] * 100)}%", 'nota': nota})
    pontos = simulacao.get('pontos_novos', 0)
    if pontos > 0:
        detalhes.append({'titulo': 'Por ponto, por mês',
                         'valor': f"{_moeda_curta(economia / pontos)} × {_moeda_curta(segmento['custo_ponto'])}",
                         'nota': 'Economia e custo do sensor'})
    if simulacao.get('economia_max', 0) > 0:
        detalhes.append({'titulo': 'Economia no período', 'valor': moeda_estimada(economia_periodo),
                         'nota': (f"Pela faixa dos estudos: {moeda_estimada(simulacao['economia_min'])} a "
                                  f"{moeda_estimada(simulacao['economia_max'])}")})

    return {
        'meta': meta, 'sem_perdas': False, 'cobre': cobre, 'titulo': titulo, 'sub': sub,
        'cobertura': min(round(economia / custo * 100), 100),
        'perdas': moeda_estimada(total_sem / meses) if meses > 0 else moeda_estimada(total_sem),
        'economia': moeda_estimada(economia), 'origem': origem,
        'custo': moeda_estimada(custo),
        'custo_faixa': f"Faixa de mercado: {faixa_investimento(simulacao.get('custo_mensal_min', 0), simulacao.get('custo_mensal_max', 0), curta=True)}",
        'saldo_titulo': 'Sobra por mês' if cobre else 'Para cobrir 100%',
        'saldo': moeda_estimada(saldo) if cobre else f"+ {moeda_estimada(-saldo)}",
        'saldo_nota': 'Depois de pagar os sensores' if cobre else 'de economia por mês',
        'detalhes': detalhes,
    }


def dashboard(request):
    simulacao = request.session.get(CHAVE_SESSAO)
    if not simulacao or 'total_sem_iot' not in simulacao:
        return redirect('formulario_simulador')

    # roda de novo a simulação (mesma semente, mesmo resultado): traz os textos do resultado
    # (como calculamos, fontes) e completa na sessão os valores que versões antigas não guardavam
    resultado = _calcular(simulacao)
    request.session[CHAVE_SESSAO] = simulacao

    segmento = SEGMENTOS.get(simulacao.get('tipo_industria'), SEGMENTOS['padrao'])
    entradas, _ = _entradas_e_referencias(simulacao, segmento)
    painel = _painel(simulacao, segmento)

    contexto = {
        'painel': painel,
        'grafico': None if painel['sem_perdas'] else _grafico_periodos(simulacao),
        'cenarios': None if painel['sem_perdas'] else _cenarios(simulacao, segmento),
        'regua': None if painel['sem_perdas'] else _regua(simulacao, segmento),
        'caminhos': None if painel['sem_perdas'] or painel['cobre'] else _caminhos(simulacao, segmento),
        'entradas': entradas,
        'como_calculamos': resultado['como_calculamos'],
        'fontes': resultado['fontes'],
        'link_diagnostico': resultado['link_diagnostico'],
        'sensores_atuais': resultado['sensores_atuais'],
    }
    return render(request, 'dashboard/index.html', contexto)
