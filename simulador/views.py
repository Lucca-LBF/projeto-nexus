from django.shortcuts import render, redirect
import pandas as pd
import numpy as np
from .forms import DadosEmpresaForm
from .segmentos import (ACOMPANHAMENTO_RESUMO, COBERTURA_SENSORES, PERCENTUAIS_ESTIMATIVA,
                        REGIME_FUNCIONAMENTO, REGIME_PADRAO, SEGMENTOS, segmentos_para_formulario)
from .feedback import explicar_calculo, link_diagnostico, montar_feedback, montar_sensores_atuais

# chave da sessão onde ficam os dados da última simulação
CHAVE_SESSAO = 'simulacao'


def _limpo(valor):
    # 2000.0 vira 2000, para o formulário não mostrar casa decimal à toa
    return int(valor) if float(valor).is_integer() else valor


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
    return _regime(REGIME_PADRAO)


def _tela_formulario(request, form, tem_memoria):
    return render(request, 'simulador/simulador.html', {
        'form': form,
        'tem_memoria': tem_memoria,
        'segmentos': segmentos_para_formulario(),
        'percentuais_estimativa': PERCENTUAIS_ESTIMATIVA,
    })


def _calcular(salvo):
    """Roda a simulação para os dados guardados em `salvo` e devolve o contexto do resultado.

    Também grava em `salvo` os totais e as séries do gráfico (o dashboard e o relatório leem de lá).
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
    # o investimento é estimado pelo tipo de empresa (custo_ponto do catálogo) e não aparece na tela
    pontos_novos = num_maquinas * fator_novo
    investimento_periodo = pontos_novos * segmento['custo_ponto'] * meses_simulados

    resultado_liquido = economia_bruta - investimento_periodo

    salvo.update({
        'total_sem_iot': float(total_operacional_antigo),
        'total_com_iot': float(total_operacional_novo),
        'economia_bruta': float(economia_bruta),
        'economia_paradas': float(economia_paradas),
        'investimento_periodo': float(investimento_periodo),
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

    if resultado_liquido >= 0:
        texto_economia = f"R$ {resultado_liquido:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        cor_economia = "text-success"
        titulo_resultado = f"LUCRO LÍQUIDO ({dias_simulados} DIAS)"
    else:
        texto_economia = f"- R$ {abs(resultado_liquido):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        cor_economia = "text-danger"
        titulo_resultado = f"PREJUÍZO ({dias_simulados} DIAS)"

    contexto = {
        'num_maquinas': num_maquinas,
        'custo_hora_parada': int(custo_hora_parada),
        'dias_simulados': dias_simulados,
        'nome_industria': nome_industria,

        'titulo_resultado': titulo_resultado,
        'economia_mensal': texto_economia,
        'cor_economia': cor_economia,
        'roi': f"{roi:.1f}%",
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
    )
    contexto['como_calculamos'] = explicar_calculo(
        segmento, {**salvo, 'custo_hora_parada': custo_hora_parada, 'perda_mensal': perda_mensal,
                   'conserto_mensal': conserto_mensal},
        texto_regime, fator_regime, dias_simulados, economia_conserto,
        cobertura=cobertura, economia_potencial=economia_potencial, economia_ja_aproveitada=economia_ja_aproveitada)
    contexto['sensores_atuais'] = montar_sensores_atuais(
        cobertura, economia_ja_aproveitada, float(economia_bruta), economia_potencial, dias_simulados)
    contexto['link_diagnostico'] = link_diagnostico(segmento["rotulo"], num_maquinas, unidade_pontos, contexto['roi'])
    return contexto


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


def formulario_simulador(request):
    # ?nova=1 apaga a simulação guardada e volta ao formulário padrão
    if request.GET.get('nova'):
        request.session.pop(CHAVE_SESSAO, None)
        return redirect('formulario_simulador')

    salvo = request.session.get(CHAVE_SESSAO)
    segmento = salvo.get('tipo_industria') if salvo else None
    form = DadosEmpresaForm(initial=salvo, segmento=segmento)
    return _tela_formulario(request, form, tem_memoria=bool(salvo))
