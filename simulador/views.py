import math
from django.shortcuts import render, redirect
import pandas as pd
import numpy as np
from .forms import DadosEmpresaForm
from .segmentos import (ACOMPANHAMENTO_RESUMO, COBERTURA_SENSORES, PERCENTUAIS_ESTIMATIVA,
                        REGIME_FUNCIONAMENTO, REGIME_PADRAO, SEGMENTOS, segmentos_para_formulario)
from .feedback import (explicar_calculo, faixa_investimento, link_diagnostico, moeda_inteira, montar_feedback,
                       montar_sensores_atuais)

# chave da sessão onde ficam os dados da última simulação
CHAVE_SESSAO = 'simulacao'
DIAS_POR_MES = 30

# nomes das duas séries conforme o modelo do segmento (usados no gráfico de comparação)
ROTULOS = {
    'paradas': {'sem_iot': 'Sem IoT (corretiva)', 'com_iot': 'Com IoT (preditiva)'},
    'perdas': {'sem_iot': 'Sem monitoramento', 'com_iot': 'Com monitoramento IoT'},
}


# ---------- formatação (padrão brasileiro) ----------

def _num(valor, casas=2):
    texto = f"{valor:,.{casas}f}"
    return texto.replace(',', 'X').replace('.', ',').replace('X', '.')


def _brl(valor, casas=2):
    sinal = '- ' if valor < 0 else ''
    return f"{sinal}R$ {_num(abs(valor), casas)}"


def _pct(valor, casas=1):
    return f"{_num(valor, casas)}%"


def _limpo(valor):
    # 2000.0 vira 2000, para o formulário não mostrar casa decimal à toa
    return int(valor) if float(valor).is_integer() else valor


# ---------- formulário e sessão ----------

def _dados_validados(form):
    """Transforma os dados já validados do formulário no dicionário guardado na sessão."""
    c = form.cleaned_data
    segmento = SEGMENTOS[c['tipo_industria']]
    dados = {
        'num_maquinas': c['num_maquinas'],
        'custo_hora_parada': _limpo(float(c['custo_hora_parada'])),
        'tempo_amostra': c['tempo_amostra'],
        'tipo_industria': c['tipo_industria'],
        # prioridade e conexão só personalizam o retorno; o acompanhamento atual também
        # separa a economia já aproveitada (pontos que já têm sensores) da que ainda dá para ganhar
        'prioridade': c['prioridade'],
        'acompanhamento_atual': c['acompanhamento_atual'],
        'conexao_local': c['conexao_local'],
    }
    # só os segmentos do modelo "perdas" enviam a perda mensal
    if segmento['modelo'] == 'perdas':
        dados['perda_mensal'] = _limpo(float(c['perda_mensal']))
    else:
        dados['regime_funcionamento'] = c['regime_funcionamento']
    # opcional: se ficar em branco, não entra na conta
    if c.get('conserto_mensal'):
        dados['conserto_mensal'] = _limpo(float(c['conserto_mensal']))
    return dados


def _regime(chave):
    """(fator, texto curto) do regime de funcionamento; valor desconhecido vira o padrão."""
    for valor, _, fator, texto in REGIME_FUNCIONAMENTO:
        if valor == (chave or REGIME_PADRAO):
            return fator, texto
    # valor desconhecido: tenta o padrão; se o padrão também não existir na lista,
    # usa um fator neutro em vez de chamar a si mesma para sempre
    if chave != REGIME_PADRAO:
        return _regime(REGIME_PADRAO)
    return 1.0, ''


def _tela_formulario(request, form, tem_memoria):
    return render(request, 'simulador/simulador.html', {
        'form': form,
        'tem_memoria': tem_memoria,
        'segmentos': segmentos_para_formulario(),
        'percentuais_estimativa': PERCENTUAIS_ESTIMATIVA,
    })


# ---------- (o que era o dashboard) ----------

def _indicadores(simulacao, segmento):
    """Cards do topo do painel: lista de dicts com titulo, valor, detalhe e classe."""
    total_sem = simulacao.get('total_sem_iot', 0)
    economia = simulacao.get('economia_bruta', 0)
    investimento = simulacao.get('investimento_periodo', 0)
    dias = simulacao.get('tempo_amostra', 30)
    # só os pontos que ainda não têm sensor entram no investimento
    pontos = simulacao.get('pontos_novos', simulacao.get('num_maquinas', 0))
    meses = dias / DIAS_POR_MES

    kpis = []

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
    """Duas listas de pares (rótulo, valor): o que a pessoa informou e as referências do simulador."""
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


def _dados_graficos(simulacao, segmento):
    """Só números e textos prontos para o HTML desenhar os gráficos com o Plotly.

    economia: economia estimada para cada redução de perdas (a linha é exata:
    economia = total_sem_iot * redução), com a sua simulação, a premissa de referência e o ponto de equilíbrio.
    comparativo: total do período sem e com IoT."""
    total_sem = simulacao.get('total_sem_iot', 0)
    if total_sem <= 0:
        return {'economia': None, 'comparativo': None}

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

    rotulos = ROTULOS[segmento['modelo']]
    valores = [total_sem, simulacao.get('total_com_iot', 0)]

    return {
        'economia': {
            'x': xs,
            'y': [round(total_sem * x / 100, 2) for x in xs],
            'efetiva': round(efetiva, 2),
            'efetiva_texto': _pct(efetiva),
            'economia': round(economia, 2),
            'economia_texto': _brl(economia),
            'referencia': round(referencia, 2),
            'referencia_texto': _pct(referencia, 0),
            'economia_referencia': round(total_sem * referencia / 100, 2),
            # None quando o equilíbrio fica fora do eixo (a marca não aparece)
            'equilibrio': round(equilibrio, 2) if equilibrio <= limite else None,
            'equilibrio_texto': _pct(equilibrio),
        },
        'comparativo': {
            'nomes': [rotulos['sem_iot'], rotulos['com_iot']],
            'valores': [round(v, 2) for v in valores],
            'textos': [_brl(v, 0) for v in valores],
        },
    }


# ---------- cálculo da simulação ----------

def _calcular(salvo):
    """Roda a simulação para os dados guardados em `salvo` e devolve o contexto do resultado.

    Também grava em `salvo` os totais e as séries do gráfico.
    Quem chama é responsável por guardar `salvo` na sessão."""
    num_maquinas = salvo['num_maquinas']
    custo_hora_parada = salvo.get('custo_hora_parada', 5000)
    dias_simulados = salvo['tempo_amostra']
    tipo_industria = salvo.get('tipo_industria', 'padrao')
    perda_mensal = salvo.get('perda_mensal', 0)
    conserto_mensal = salvo.get('conserto_mensal', 0)
    fator_regime, texto_regime = _regime(salvo.get('regime_funcionamento'))

    np.random.seed(42)

    # taxa de falha, redução com IoT e nome vêm do catálogo (segmentos.py)
    segmento = SEGMENTOS.get(tipo_industria, SEGMENTOS['padrao'])
    taxa_falha_base = segmento['taxa_falha_base']
    reducao_iot = segmento['reducao_iot']
    nome_industria = segmento['nome']

    if segmento['modelo'] == 'perdas':
        # o usuário informa quanto perde por mês; espalhamos por dia com variação
        perda_diaria = perda_mensal / 30
        custo_diario_sem_iot = np.random.normal(loc=perda_diaria, scale=perda_diaria * 0.3, size=dias_simulados)
        custo_diario_sem_iot = np.clip(custo_diario_sem_iot, perda_diaria * 0.2, None)

        ruido_iot = np.random.normal(loc=0, scale=perda_diaria * 0.05, size=dias_simulados)
        custo_diario_com_iot = custo_diario_sem_iot * (1 - reducao_iot) + ruido_iot
        custo_diario_com_iot = np.clip(custo_diario_com_iot, perda_diaria * 0.1, None)
    else:
        # o regime de funcionamento (1 turno, 2 turnos, 24 h) muda as horas de parada esperadas
        media_horas_perdidas_dia = num_maquinas * taxa_falha_base * fator_regime

        horas_paradas_sem_iot = np.random.normal(loc=media_horas_perdidas_dia, scale=media_horas_perdidas_dia * 0.3, size=dias_simulados)
        horas_paradas_sem_iot = np.clip(horas_paradas_sem_iot, media_horas_perdidas_dia * 0.2, None)
        custo_diario_sem_iot = horas_paradas_sem_iot * custo_hora_parada

        horas_paradas_com_iot = horas_paradas_sem_iot * (1 - reducao_iot)
        ruido_iot = np.random.normal(loc=0, scale=media_horas_perdidas_dia * 0.05, size=dias_simulados)
        horas_paradas_com_iot = np.clip(horas_paradas_com_iot + ruido_iot, media_horas_perdidas_dia * 0.1, None)
        custo_diario_com_iot = horas_paradas_com_iot * custo_hora_parada

    # conserto de emergência (opcional): custo fixo por dia, reduzido na mesma proporção das perdas
    conserto_diario = conserto_mensal / 30
    economia_conserto = 0.0
    if conserto_diario > 0:
        custo_diario_sem_iot = custo_diario_sem_iot + conserto_diario
        custo_diario_com_iot = custo_diario_com_iot + conserto_diario * (1 - reducao_iot)
        economia_conserto = conserto_diario * dias_simulados * reducao_iot

    # sensores que a empresa já tem: essa parte da economia já está sendo aproveitada.
    # Daqui para a frente, os números valem para a ampliação (os pontos que ainda ficam sem sensor).
    cobertura = COBERTURA_SENSORES.get(salvo.get('acompanhamento_atual'), 0.0)
    fator_novo = 1 - cobertura
    economia_potencial = float(custo_diario_sem_iot.sum() - custo_diario_com_iot.sum())
    economia_ja_aproveitada = economia_potencial * cobertura

    df = pd.DataFrame({
    'Dia': range(1, dias_simulados + 1),
    'Custo_Sem_IoT': custo_diario_sem_iot * fator_novo,
    'Custo_Com_IoT': custo_diario_com_iot * fator_novo
    })

    total_operacional_antigo = df['Custo_Sem_IoT'].sum()
    total_operacional_novo = df['Custo_Com_IoT'].sum()
    economia_bruta = total_operacional_antigo - total_operacional_novo

    # só a parte das paradas: o conserto de emergência fica de fora (também só na parte ampliada)
    economia_paradas = economia_bruta - economia_conserto * fator_novo

    meses_simulados = dias_simulados / 30
    # o investimento é estimado pelo tipo de empresa (custo_ponto do catálogo): o valor central entra no
    # lucro e no ROI, e a faixa (mínimo e máximo) é o que aparece como "investimento estimado"
    pontos_novos = num_maquinas * fator_novo
    investimento_periodo = pontos_novos * segmento['custo_ponto'] * meses_simulados
    faixa_min, faixa_max = segmento['custo_ponto_faixa']
    investimento_min = pontos_novos * faixa_min * meses_simulados
    investimento_max = pontos_novos * faixa_max * meses_simulados

    resultado_liquido = economia_bruta - investimento_periodo

    salvo.update({
        'total_sem_iot': float(total_operacional_antigo),
        'total_com_iot': float(total_operacional_novo),
        'economia_bruta': float(economia_bruta),
        'economia_paradas': float(economia_paradas),
        'investimento_periodo': float(investimento_periodo),
        'investimento_min': float(investimento_min),
        'investimento_max': float(investimento_max),
        'resultado_liquido': float(resultado_liquido),
        'cobertura': cobertura,
        'pontos_novos': float(pontos_novos),
        'economia_potencial_total': economia_potencial,
        'economia_ja_aproveitada': float(economia_ja_aproveitada),
        'dados_grafico_dias': df['Dia'].tolist(),
        'dados_grafico_sem_iot': df['Custo_Sem_IoT'].tolist(),
        'dados_grafico_com_iot': df['Custo_Com_IoT'].tolist(),
    })

    if investimento_periodo > 0:
        roi = (resultado_liquido / investimento_periodo) * 100
    else:
        roi = 0

    # equilíbrio: redução de perdas mínima para os sensores se pagarem (pelo valor central do investimento)
    equilibrio_pct = investimento_periodo / total_operacional_antigo * 100 if total_operacional_antigo > 0 else 0

    if resultado_liquido >= 0:
        texto_economia = f"R$ {resultado_liquido:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        cor_economia = "text-success"
        titulo_resultado = f"LUCRO LÍQUIDO ESTIMADO ({dias_simulados} DIAS)"
        roi_titulo = "Retorno sobre Investimento (ROI) estimado"
        roi_exibicao = f"{roi:.1f}%"
        resumo_diagnostico = f"ROI estimado de {roi:.1f}%"
    else:
        # sem valor negativo nem vermelho: mostra a economia estimada e o que falta para os sensores se pagarem
        texto_economia = f"R$ {economia_bruta:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        cor_economia = "text-info"
        titulo_resultado = f"ECONOMIA ESTIMADA ({dias_simulados} DIAS)"
        roi_titulo = "Redução de perdas para os sensores se pagarem"
        roi_exibicao = f"{equilibrio_pct:.0f}%" if equilibrio_pct < 100 else "Revisar valores"
        resumo_diagnostico = f"economia estimada de {moeda_inteira(economia_bruta)}"

    contexto = {
        'num_maquinas': num_maquinas,
        'custo_hora_parada': int(custo_hora_parada),
        'dias_simulados': dias_simulados,
        'nome_industria': nome_industria,

        'titulo_resultado': titulo_resultado,
        'economia_mensal': texto_economia,
        'cor_economia': cor_economia,
        'roi': roi_exibicao,
        'roi_titulo': roi_titulo,
        'investimento_faixa': faixa_investimento(investimento_min, investimento_max),
        'investimento_central': moeda_inteira(investimento_periodo),
        'dados_grafico_dias': df['Dia'].tolist(),
        'dados_grafico_sem_iot': df['Custo_Sem_IoT'].tolist(),
        'dados_grafico_com_iot': df['Custo_Com_IoT'].tolist(),
    }

    # resumo mostrado na lateral do resultado
    rotulo_pontos, unidade_pontos = segmento['rotulo_pontos']
    if segmento['modelo'] == 'perdas':
        linha_perda = ('Perda Mensal Estimada', f"R$ {int(perda_mensal)}")
    else:
        linha_perda = ('Custo da Hora Parada', f"R$ {int(custo_hora_parada)}")
    contexto['resumo'] = [(rotulo_pontos, f"{num_maquinas} {unidade_pontos}")]
    if segmento['modelo'] == 'paradas':
        contexto['resumo'].append(('Funcionamento', texto_regime))
    contexto['resumo'].append(linha_perda)
    if conserto_diario > 0:
        contexto['resumo'].append(('Conserto de Emergência', f"R$ {_limpo(conserto_mensal)} por mês"))
    contexto['resumo'].append(('Sensores Atuais', ACOMPANHAMENTO_RESUMO.get(salvo.get('acompanhamento_atual'), 'Não informado')))

    contexto['feedback'] = montar_feedback(
        segmento, roi, economia_bruta, investimento_periodo, total_operacional_antigo,
        prioridade=salvo.get('prioridade'),
        acompanhamento=salvo.get('acompanhamento_atual'),
        conexao_local=salvo.get('conexao_local'),
        investimento_min=investimento_min,
    )
    contexto['como_calculamos'] = explicar_calculo(
        segmento, {**salvo, 'custo_hora_parada': custo_hora_parada, 'perda_mensal': perda_mensal,
                   'conserto_mensal': conserto_mensal},
        texto_regime, fator_regime, dias_simulados, economia_conserto,
        cobertura=cobertura, economia_potencial=economia_potencial, economia_ja_aproveitada=economia_ja_aproveitada,
        investimento_min=investimento_min, investimento_max=investimento_max)
    contexto['sensores_atuais'] = montar_sensores_atuais(
        cobertura, economia_ja_aproveitada, float(economia_bruta), economia_potencial, dias_simulados)
    contexto['link_diagnostico'] = link_diagnostico(segmento["rotulo"], num_maquinas, unidade_pontos, resumo_diagnostico)

    # painel de resultados (o que era o dashboard): indicadores, premissas e dados dos gráficos
    contexto['kpis'] = _indicadores(salvo, segmento)
    contexto['entradas'], contexto['referencias'] = _entradas_e_referencias(salvo, segmento)
    contexto['premissa_confirmada'] = segmento.get('premissa_confirmada', True)
    contexto['sem_perdas'] = total_operacional_antigo <= 0
    contexto['graficos'] = _dados_graficos(salvo, segmento)
    return contexto


# ---------- views ----------

def calcular_simulacao(request):
    if request.method == 'POST':
        # o servidor valida tudo de novo: o navegador pode ser contornado
        form = DadosEmpresaForm(request.POST, segmento=request.POST.get('tipo_industria'))
        if not form.is_valid():
            return _tela_formulario(request, form, tem_memoria=bool(request.session.get(CHAVE_SESSAO)))
        salvo = _dados_validados(form)
        request.session[CHAVE_SESSAO] = salvo
    else:
        salvo = request.session.get(CHAVE_SESSAO)
        # sem simulação guardada não há o que mostrar: volta ao formulário
        if not salvo or 'num_maquinas' not in salvo:
            return redirect('formulario_simulador')

    contexto = _calcular(salvo)
    request.session[CHAVE_SESSAO] = salvo
    request.session.modified = True
    return render(request, 'simulador/resultado.html', contexto)

def relatorio(request):
    """Relatório completo para salvar em PDF: resultado e painel na mesma página.
 
    O PDF não é gerado no servidor: a página abre a impressão do navegador ("Salvar como PDF")."""
    salvo = request.session.get(CHAVE_SESSAO)
    # sem simulação guardada não há o que mostrar: volta ao formulário
    if not salvo or 'num_maquinas' not in salvo:
        return redirect('formulario_simulador')
 
    # roda de novo a simulação (mesma semente): garante totais e séries atualizados
    contexto = _calcular(salvo)
    request.session[CHAVE_SESSAO] = salvo
    request.session.modified = True
 
    liquido = salvo.get('resultado_liquido', 0)
    dias = contexto['dias_simulados']
    contexto.update({
        'dias': dias,
        # sem valor negativo: quando não paga, o destaque deixa de ser verde
        'tem_retorno': liquido >= 0,
        # sem valor negativo nem vermelho: quando o lucro é negativo, mostra a economia estimada
        'lucro_titulo': (f"Resultado líquido estimado ({dias} dias)" if liquido >= 0
                         else f"Economia estimada ({dias} dias)"),
        'lucro': _brl(liquido) if liquido >= 0 else _brl(salvo.get('economia_bruta', 0)),
        'imprimir': request.GET.get('imprimir') == '1',
    })
    return render(request, 'simulador/relatorio.html', contexto)


def formulario_simulador(request):
    # ?nova=1 apaga a simulação guardada e volta ao formulário padrão
    if request.GET.get('nova'):
        request.session.pop(CHAVE_SESSAO, None)
        return redirect('formulario_simulador')

    salvo = request.session.get(CHAVE_SESSAO)
    segmento = salvo.get('tipo_industria') if salvo else None
    form = DadosEmpresaForm(initial=salvo, segmento=segmento)
    return _tela_formulario(request, form, tem_memoria=bool(salvo))
