from django.shortcuts import render, redirect
import pandas as pd
import numpy as np
from .forms import DadosEmpresaForm
from .segmentos import (PERCENTUAIS_ESTIMATIVA, REGIME_FUNCIONAMENTO, REGIME_PADRAO,
                        SEGMENTOS, segmentos_para_formulario)
from .feedback import explicar_calculo, link_diagnostico, montar_feedback

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
        'custo_sensor_iot': _limpo(float(c['custo_sensor_iot'])),
        'tempo_amostra': c['tempo_amostra'],
        'tipo_industria': c['tipo_industria'],
        # perguntas de contexto: só personalizam o retorno, não entram na conta
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

    num_maquinas = salvo['num_maquinas']
    custo_hora_parada = salvo.get('custo_hora_parada', 5000)
    custo_sensor_iot = salvo['custo_sensor_iot']
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

    df = pd.DataFrame({
        'Dia': range(1, dias_simulados + 1),
        'Custo_Sem_IoT': custo_diario_sem_iot,
        'Custo_Com_IoT': custo_diario_com_iot
    })


    total_operacional_antigo = df['Custo_Sem_IoT'].sum()
    total_operacional_novo = df['Custo_Com_IoT'].sum()
    economia_bruta = total_operacional_antigo - total_operacional_novo

    # o dashboard separa a economia em categorias: paradas (ou perdas), manutenção e energia
    economia_paradas = economia_bruta - economia_conserto
    # Exemplo (20%, 15%): usado enquanto a pessoa não informa o gasto com conserto de emergência
    custo_manutencao_periodo = total_operacional_antigo * 0.20
    custo_energia_periodo = total_operacional_antigo * 0.15
    # Economia estimada proporcional à redução das falhas
    economia_manutencao = custo_manutencao_periodo * reducao_iot
    economia_energia = custo_energia_periodo * reducao_iot
    if conserto_diario > 0:
        # com o valor real informado, a manutenção deixa de ser exemplo
        economia_manutencao = economia_conserto

    meses_simulados = dias_simulados / 30
    investimento_periodo = (num_maquinas * custo_sensor_iot) * meses_simulados

    resultado_liquido = economia_bruta - investimento_periodo

    request.session[CHAVE_SESSAO].update({
        'total_sem_iot': float(total_operacional_antigo),
        'total_com_iot': float(total_operacional_novo),
        'economia_bruta': float(economia_bruta),
        'economia_paradas': float(economia_paradas),
        'economia_manutencao': float(economia_manutencao),
        'economia_energia': float(economia_energia),
        'investimento_periodo': float(investimento_periodo),
        'resultado_liquido': float(resultado_liquido),
        'dados_grafico_dias': df['Dia'].tolist(),
        'dados_grafico_sem_iot': df['Custo_Sem_IoT'].tolist(),
        'dados_grafico_com_iot': df['Custo_Com_IoT'].tolist(),
    })
    request.session.modified = True

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
        'custo_sensor_iot': int(custo_sensor_iot),
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
    contexto['resumo'].append(('Custo Mensal do Sensor', f"R$ {int(custo_sensor_iot)}"))

    contexto['feedback'] = montar_feedback(
        segmento, roi, economia_bruta, investimento_periodo, total_operacional_antigo,
        prioridade=salvo.get('prioridade'),
        acompanhamento=salvo.get('acompanhamento_atual'),
        conexao_local=salvo.get('conexao_local'),
    )
    contexto['como_calculamos'] = explicar_calculo(
        segmento, {**salvo, 'custo_hora_parada': custo_hora_parada, 'perda_mensal': perda_mensal,
                   'conserto_mensal': conserto_mensal},
        texto_regime, fator_regime, dias_simulados, investimento_periodo, economia_conserto)
    contexto['link_diagnostico'] = link_diagnostico(segmento["rotulo"], num_maquinas, unidade_pontos, contexto['roi'])

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
