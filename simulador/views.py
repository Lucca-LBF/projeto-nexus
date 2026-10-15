from django.shortcuts import render, redirect
import pandas as pd
import numpy as np
from .forms import DadosEmpresaForm
from .segmentos import (ACOMPANHAMENTO, CONEXAO_LOCAL, PERCENTUAIS_ESTIMATIVA, SEGMENTOS,
                        opcoes_prioridade, segmentos_para_formulario)
from .feedback import montar_feedback

# chave da sessão onde ficam os dados da última simulação
CHAVE_SESSAO = 'simulacao'


def _limpo(valor):
    # 2000.0 vira 2000, para o formulário não mostrar casa decimal à toa
    return int(valor) if float(valor).is_integer() else valor


def _escolha(valor, validos, padrao):
    # aceita só valores que existem nas opções (o POST pode vir adulterado)
    return valor if valor in validos else padrao


def calcular_simulacao(request):
    if request.method == 'POST':
        num_maquinas = int(request.POST.get('num_maquinas', 100))
        custo_hora_parada = float(request.POST.get('custo_hora_parada', 5000))
        custo_sensor_iot = float(request.POST.get('custo_sensor_iot', 300))
        dias_simulados = int(request.POST.get('tempo_amostra', 30))
        tipo_industria = request.POST.get('tipo_industria', 'padrao')
        # só os segmentos do modelo "perdas" enviam este campo
        perda_mensal = max(float(request.POST.get('perda_mensal') or 0), 0)

        salvo = {
            'num_maquinas': num_maquinas,
            'custo_hora_parada': _limpo(custo_hora_parada),
            'custo_sensor_iot': _limpo(custo_sensor_iot),
            'tempo_amostra': dias_simulados,
            'tipo_industria': tipo_industria,
        }
        if request.POST.get('perda_mensal'):
            salvo['perda_mensal'] = _limpo(perda_mensal)
        # perguntas de contexto: só personalizam o retorno, não entram na conta
        opcoes = [valor for valor, _ in opcoes_prioridade(tipo_industria)]
        salvo['prioridade'] = _escolha(request.POST.get('prioridade'), opcoes, opcoes[0])
        salvo['acompanhamento_atual'] = _escolha(
            request.POST.get('acompanhamento_atual'), [i[0] for i in ACOMPANHAMENTO], 'manual')
        salvo['conexao_local'] = _escolha(
            request.POST.get('conexao_local'), [i[0] for i in CONEXAO_LOCAL], 'nao_sei')
        request.session[CHAVE_SESSAO] = salvo
    else:
        salvo = request.session.get(CHAVE_SESSAO, {})
        num_maquinas = salvo.get('num_maquinas', 40)
        custo_hora_parada = salvo.get('custo_hora_parada', 1500.0)
        custo_sensor_iot = salvo.get('custo_sensor_iot', 35.0)
        dias_simulados = salvo.get('tempo_amostra', 30)
        tipo_industria = salvo.get('tipo_industria', 'padrao')
        perda_mensal = salvo.get('perda_mensal', 0)

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
        media_horas_perdidas_dia = num_maquinas * taxa_falha_base

        horas_paradas_sem_iot = np.random.normal(loc=media_horas_perdidas_dia, scale=media_horas_perdidas_dia * 0.3, size=dias_simulados)
        horas_paradas_sem_iot = np.clip(horas_paradas_sem_iot, media_horas_perdidas_dia * 0.2, None)
        custo_diario_sem_iot = horas_paradas_sem_iot * custo_hora_parada

        horas_paradas_com_iot = horas_paradas_sem_iot * (1 - reducao_iot)
        ruido_iot = np.random.normal(loc=0, scale=media_horas_perdidas_dia * 0.05, size=dias_simulados)
        horas_paradas_com_iot = np.clip(horas_paradas_com_iot + ruido_iot, media_horas_perdidas_dia * 0.1, None)
        custo_diario_com_iot = horas_paradas_com_iot * custo_hora_parada

    df = pd.DataFrame({
        'Dia': range(1, dias_simulados + 1),
        'Custo_Sem_IoT': custo_diario_sem_iot,
        'Custo_Com_IoT': custo_diario_com_iot
    })


    total_operacional_antigo = df['Custo_Sem_IoT'].sum()
    total_operacional_novo = df['Custo_Com_IoT'].sum()
    economia_bruta = total_operacional_antigo - total_operacional_novo

    economia_paradas = economia_bruta
    # Exemplo (20%, 15%)
    custo_manutencao_periodo = total_operacional_antigo * 0.20
    custo_energia_periodo = total_operacional_antigo * 0.15
    # Economia estimada proporcional à redução das falhas
    economia_manutencao = custo_manutencao_periodo * reducao_iot
    economia_energia = custo_energia_periodo * reducao_iot
    
    meses_simulados = dias_simulados / 30
    investimento_periodo = (num_maquinas * custo_sensor_iot) * meses_simulados
    
    resultado_liquido = economia_bruta - investimento_periodo

    salvo.update({
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
    request.session[CHAVE_SESSAO] = salvo
    
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
    contexto['resumo'] = [
        (rotulo_pontos, f"{num_maquinas} {unidade_pontos}"),
        linha_perda,
        ('Custo Mensal do Sensor', f"R$ {int(custo_sensor_iot)}"),
    ]
    contexto['feedback'] = montar_feedback(
        segmento, roi, economia_bruta, investimento_periodo, total_operacional_antigo,
        prioridade=salvo.get('prioridade'),
        acompanhamento=salvo.get('acompanhamento_atual'),
        conexao_local=salvo.get('conexao_local'),
    )

    return render(request, 'simulador/resultado.html', contexto)


def formulario_simulador(request):
    # ?nova=1 apaga a simulação guardada e volta ao formulário padrão
    if request.GET.get('nova'):
        request.session.pop(CHAVE_SESSAO, None)
        return redirect('formulario_simulador')

    salvo = request.session.get(CHAVE_SESSAO)
    segmento = salvo.get('tipo_industria') if salvo else None
    form = DadosEmpresaForm(initial=salvo, segmento=segmento)
    return render(request, 'simulador/simulador.html', {
        'form': form,
        'tem_memoria': bool(salvo),
        'segmentos': segmentos_para_formulario(),
        'percentuais_estimativa': PERCENTUAIS_ESTIMATIVA,
    })