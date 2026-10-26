import math
from django.shortcuts import render, redirect
import pandas as pd
import numpy as np
from .forms import DadosEmpresaForm
from .segmentos import (ACOMPANHAMENTO_RESUMO, COBERTURA_SENSORES, PERCENTUAIS_ESTIMATIVA,
                        REGIME_FUNCIONAMENTO, REGIME_PADRAO, SEGMENTOS, segmentos_para_formulario)
from .feedback import (explicar_calculo, faixa_investimento, faixa_roi, link_diagnostico, moeda_inteira,
                       montar_feedback, montar_sensores_atuais)

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
       # 1. FATOR DE ESCALA: Evita que muitas máquinas multipliquem o tempo de parada de forma irreal
        fator_escala_maquinas = math.sqrt(num_maquinas)
        
        # 2. CALCULA A MÉDIA DE HORAS PERDIDAS POR DIA USANDO A ESCALA
        media_horas_perdidas_dia = fator_escala_maquinas * taxa_falha_base * fator_regime
        
        # 3. TETO DE 10%: A fábrica inteira não pode parar mais do que 10% do seu tempo diário.
        # (Se fator_regime for em horas ex: 16, teto é 1.6 horas/dia. Se for um multiplicador 1, 2, 3, estimamos em 8h por turno)
        horas_trabalhadas_dia = fator_regime if fator_regime >= 8 else fator_regime * 8
        teto_diario = horas_trabalhadas_dia * 0.10
        if media_horas_perdidas_dia > teto_diario:
            media_horas_perdidas_dia = teto_diario

        # 4. GERAÇÃO DOS DIAS COM NUMPY USANDO A MÉDIA CORRIGIDA
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

    # o que falta para os sensores se pagarem: a redução de perdas necessária ou, se nem 100% bastaria,
    # o valor que a hora parada (ou a perda mensal) teria que ter. Sempre é um caminho, nunca "revise os dados".
    valor_equilibrio = 0.0
    if equilibrio_pct < 100:
        falta_curto = f"Os sensores se pagam se evitarem pelo menos {equilibrio_pct:.0f}% das perdas."
        falta_pagar = (f"Pela estimativa, os sensores se pagam se as perdas caírem pelo menos {equilibrio_pct:.1f}%. "
                       f"A referência do seu setor é {round(segmento['reducao_iot'] * 100)}%.".replace('.', ',', 1))
    else:
        # a economia principal (sem o conserto de emergência) cresce na mesma proporção do valor informado
        economia_principal = economia_bruta - economia_conserto * fator_novo
        informado = custo_hora_parada if segmento['modelo'] == 'paradas' else perda_mensal
        if economia_principal > 0 and informado > 0:
            faltante = max(investimento_periodo - economia_conserto * fator_novo, 0)
            valor_equilibrio = float(informado * faltante / economia_principal)
        if segmento['modelo'] == 'paradas':
            grandeza, unidade_grandeza = "cada hora parada custasse", "a hora"
        else:
            grandeza, unidade_grandeza = "a perda mensal fosse de", "por mês"
        if valor_equilibrio > 0:
            falta_curto = f"Os sensores se pagam se {grandeza} cerca de {moeda_inteira(valor_equilibrio)}."
            falta_pagar = (f"Com os valores informados, a economia fica abaixo do investimento estimado, e nem evitar "
                           f"todas as perdas pagaria os sensores. Eles se pagariam se {grandeza} cerca de "
                           f"{moeda_inteira(valor_equilibrio)} (você informou {moeda_inteira(informado)}). "
                           "Vale começar por poucos pontos críticos, onde a perda é maior.")
        else:
            falta_curto = "Vale começar por poucos pontos críticos, onde a perda é maior."
            falta_pagar = falta_curto

    # o dashboard lê estes valores da sessão
    salvo.update({
        'equilibrio_pct': float(equilibrio_pct),
        'valor_equilibrio': float(valor_equilibrio),
        'valor_informado': float(custo_hora_parada if segmento['modelo'] == 'paradas' else perda_mensal),
    })
    roi_faixa = faixa_roi(economia_bruta, investimento_min, investimento_max)
    roi_titulo = "Retorno sobre Investimento (ROI) estimado"
    if resultado_liquido >= 0:
        texto_economia = f"R$ {resultado_liquido:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        cor_economia = "text-success"
        titulo_resultado = f"LUCRO LÍQUIDO ESTIMADO ({dias_simulados} DIAS)"
        roi_exibicao = f"{roi:.1f}%"
        roi_nota = f"Pela faixa de investimento: {roi_faixa}" if roi_faixa else ""
        resumo_diagnostico = f"ROI estimado de {roi:.1f}%"
    else:
        # sem vermelho: mostra a economia estimada, o ROI em faixa e o que falta para os sensores se pagarem
        texto_economia = f"R$ {economia_bruta:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        cor_economia = "text-info"
        titulo_resultado = f"ECONOMIA ESTIMADA ({dias_simulados} DIAS)"
        roi_exibicao = roi_faixa or "—"
        roi_nota = falta_curto
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
        'roi_nota': roi_nota,
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
        falta_pagar=falta_pagar,
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
