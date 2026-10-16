"""Monta o retorno que a empresa recebe junto com o resultado da simulação."""

from urllib.parse import quote

from .segmentos import ACOMPANHAMENTO, CONEXAO_LOCAL

SITE_BZU = "https://bzutech.com.br"
# contato da Bzu (o mesmo do site deles): o botão "Pedir diagnóstico" abre uma conversa já com a mensagem pronta
WHATSAPP_BZU = "5581992259287"
EMAIL_BZU = "bzu@bzutech.com"

# o ROI conta só o custo dos sensores: o resto a Bzu define na proposta
ESCOPO = ("Esta estimativa considera só o custo dos sensores. Gateways, a plataforma (BZU Cloud) "
          "e o diagnóstico não entram nesta conta: a Bzu define esses itens na proposta.")


def _num(valor, casas=2):
    """1234.5 -> '1.234,50' (formato brasileiro)."""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def moeda(valor):
    """1234.5 -> 'R$ 1.234,50'."""
    return f"R$ {_num(valor)}"


def link_diagnostico(nome_industria, num_pontos, unidade, roi_texto):
    """Link do WhatsApp da Bzu com a mensagem pronta (só segmento, quantidade e ROI, nada pessoal)."""
    mensagem = (f"Olá, Bzu! Fiz uma simulação no simulador de economia com IoT (segmento: {nome_industria}, "
                f"{num_pontos} {unidade.lower()}, ROI estimado de {roi_texto}) e gostaria de pedir um diagnóstico.")
    return f"https://wa.me/{WHATSAPP_BZU}?text={quote(mensagem)}"


def explicar_calculo(segmento, dados, regime_texto, fator_regime, dias, investimento_periodo, economia_conserto):
    """Passo a passo da conta, em frases, usando os números da própria simulação."""
    reducao = segmento["reducao_iot"]
    meses = dias // 30
    passos = []

    if segmento["modelo"] == "perdas":
        perda_periodo = dados["perda_mensal"] * dias / 30
        passos.append(f"Perda estimada: {moeda(dados['perda_mensal'])} por mês, ou cerca de "
                      f"{moeda(perda_periodo)} em {dias} dias sem sensores.")
    else:
        horas_dia = dados["num_maquinas"] * segmento["taxa_falha_base"] * fator_regime
        passos.append(f"Paradas por dia: {dados['num_maquinas']} máquinas × {_num(segmento['taxa_falha_base'])} hora de parada "
                      f"por máquina por dia × {_num(fator_regime, 1)} ({regime_texto}) = cerca de {_num(horas_dia, 1)} horas.")
        passos.append(f"Cada hora parada custa {moeda(dados['custo_hora_parada'])}, então, sem sensores, as paradas "
                      f"custariam cerca de {moeda(horas_dia * dias * dados['custo_hora_parada'])} em {dias} dias.")

    passos.append(f"Com sensores e alertas, a estimativa é evitar {round(reducao * 100)}% dessas perdas "
                  "(premissa de referência do simulador).")
    if economia_conserto > 0:
        passos.append(f"Conserto de emergência: {moeda(dados['conserto_mensal'])} por mês informados. Com a mesma redução, "
                      f"a economia é de {moeda(economia_conserto)} no período.")
    passos.append(f"Investimento: {dados['num_maquinas']} sensores × {moeda(dados['custo_sensor_iot'])} por mês × "
                  f"{meses} {'mês' if meses == 1 else 'meses'} = {moeda(investimento_periodo)}.")
    passos.append("Lucro líquido = economia − investimento. ROI = lucro líquido ÷ investimento.")
    passos.append("Os valores de cada dia variam em torno da média (a simulação usa uma variação fixa), "
                  "por isso o total pode diferir um pouco da conta simples acima.")
    return passos


def _achar(lista, valor, posicao):
    """Procura o valor numa lista de tuplas e devolve o item `posicao` (ou None)."""
    for item in lista:
        if item[0] == valor:
            return item[posicao]
    return None


def montar_feedback(segmento, roi, economia_bruta, investimento_periodo, perda_total_sem_iot,
                    prioridade=None, acompanhamento=None, conexao_local=None):
    reducao = segmento["reducao_iot"]

    if roi < 0:
        leitura = ("Com esses números, o investimento não se paga no período. "
                   "Reveja o custo do sensor ou a quantidade de pontos, ou simule um período maior.")
        classe = "text-danger"
    elif roi < 100:
        leitura = "O retorno é positivo, mas moderado. Vale começar por um piloto nos pontos mais críticos."
        classe = "text-info"
    else:
        leitura = ("O retorno é alto: a economia estimada é pelo menos o dobro do investimento. "
                   "Vale validar os números com um diagnóstico.")
        classe = "text-success"

    retorno = ""
    if investimento_periodo > 0:
        retorno = (f"A cada R$ 1,00 investido em sensores, a estimativa é evitar "
                   f"R$ {_num(economia_bruta / investimento_periodo)} em perdas.")

    equilibrio = ""
    if investimento_periodo > 0 and perda_total_sem_iot > 0:
        pct = investimento_periodo / perda_total_sem_iot * 100
        if pct >= 100:
            equilibrio = ("Os sensores custam mais do que toda a perda estimada. "
                          "Reveja o custo do sensor ou a quantidade de pontos.")
        else:
            equilibrio = (f"Mesmo que o resultado real fique abaixo do estimado, os sensores se pagam "
                          f"se as perdas caírem pelo menos {_num(pct, 1)}%.")

    # respostas das perguntas de contexto (não entram na conta do ROI)
    prioridade_texto = _achar(segmento["prioridades"], prioridade, 1)
    comece_por = _achar(segmento["prioridades"], prioridade, 2)
    acompanhamento_texto = _achar(ACOMPANHAMENTO, acompanhamento, 2)
    conexao = _achar(CONEXAO_LOCAL, conexao_local, 2) or segmento["conexao"]

    return {
        "prioridade": prioridade_texto,
        "comece_por": comece_por,
        "acompanhamento": acompanhamento_texto,
        "leitura": leitura,
        "classe": classe,
        "retorno": retorno,
        "equilibrio": equilibrio,
        "monitorar": segmento["monitorar"],
        "conexao": conexao,
        "caso": segmento["caso"],
        "premissa": (f"Estimativa feita com redução de {round(reducao * 100)}% das perdas, "
                     "uma premissa de referência do simulador. O resultado real depende do seu cenário."),
        "site": SITE_BZU,
        "email": EMAIL_BZU,
        "escopo": ESCOPO,
    }
