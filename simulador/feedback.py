"""Monta o retorno que a empresa recebe junto com o resultado da simulação."""

from urllib.parse import quote

from .segmentos import ACOMPANHAMENTO, CONEXAO_LOCAL

SITE_BZU = "https://bzutech.com.br"
# contato da Bzu (o mesmo do site deles): o botão "Pedir diagnóstico" abre uma conversa já com a mensagem pronta
WHATSAPP_BZU = "5581992259287"
EMAIL_BZU = "bzu@bzutech.com"

# o investimento é uma faixa de mercado para o tipo de empresa e conta só os sensores: o resto a Bzu define na proposta
ESCOPO = ("O investimento é uma estimativa de mercado para o seu tipo de empresa, em faixa, e considera só os sensores. "
          "Não é preço da Bzu. Gateways, a plataforma (BZU Cloud) e o diagnóstico não entram nesta conta: "
          "a Bzu define o valor final e esses itens na proposta.")


# vale para todos os setores: o ganho de medir o tempo todo, sem depender de rondas e anotações
TEMPO_REAL = ("Os sensores medem 24 horas por dia e avisam em tempo real quando algo sai do normal. "
              "O acompanhamento deixa de depender de rondas, anotações e da memória de alguém, e o problema "
              "pode ser tratado antes de virar parada. Os ganhos acima são estimativas: o diagnóstico "
              "confirma quanto disso se aplica ao seu cenário.")


def _num(valor, casas=2):
    """1234.5 -> '1.234,50' (formato brasileiro)."""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def moeda(valor):
    """1234.5 -> 'R$ 1.234,50'."""
    return f"R$ {_num(valor)}"


def _arredondar(valor):
    """Arredonda para a estimativa não parecer exata: R$ 10 até 10 mil, R$ 100 até 100 mil, R$ 1.000 acima."""
    passo = 10 if valor < 10_000 else 100 if valor < 100_000 else 1_000
    return round(valor / passo) * passo


def moeda_inteira(valor):
    """1234.5 -> 'R$ 1.230' (arredondado, sem centavos)."""
    return f"R$ {_num(_arredondar(valor), 0)}"


def faixa_investimento(minimo, maximo, curta=False):
    """Faixa de investimento em texto: 'entre R$ 4.100 e R$ 9.900' (ou 'R$ 4.100 a R$ 9.900', se curta)."""
    if curta:
        return f"{moeda_inteira(minimo)} a {moeda_inteira(maximo)}"
    return f"entre {moeda_inteira(minimo)} e {moeda_inteira(maximo)}"


def link_diagnostico(nome_industria, num_pontos, unidade, resumo_texto):
    """Link do WhatsApp da Bzu com a mensagem pronta (só segmento, quantidade e estimativa, nada pessoal)."""
    mensagem = (f"Olá, Bzu! Fiz uma simulação no simulador de economia com IoT (segmento: {nome_industria}, "
                f"{num_pontos} {unidade.lower()}, {resumo_texto}) e gostaria de pedir um diagnóstico.")
    return f"https://wa.me/{WHATSAPP_BZU}?text={quote(mensagem)}"


def montar_sensores_atuais(cobertura, economia_ja, economia_nova, economia_total, dias):
    """Resumo para quem já tem sensores: o que já é aproveitado e o que ainda dá para ganhar ampliando.

    Devolve None quando a empresa não tem sensores (nada a mostrar)."""
    if cobertura <= 0:
        return None
    pct = round(cobertura * 100)
    return {
        "pct": pct,
        "pct_restante": 100 - pct,
        "ja": moeda(economia_ja),
        "nova": moeda(economia_nova),
        "total": moeda(economia_total),
        "dias": dias,
        "texto": (f"Seus sensores atuais, em cerca de {pct}% dos pontos, já evitam cerca de {moeda(economia_ja)} "
                  f"em {dias} dias. Ampliar o monitoramento para os outros {100 - pct}% dos pontos pode evitar "
                  f"mais {moeda(economia_nova)}, chegando a {moeda(economia_total)} no período."),
        "sugestao": ("Sugestão: ampliar a cobertura para os pontos que ainda ficam sem sensor e revisar, "
                     "num diagnóstico, a qualidade dos sensores que já existem."),
    }


def explicar_calculo(segmento, dados, regime_texto, fator_regime, dias, economia_conserto,
                     cobertura=0.0, economia_potencial=0.0, economia_ja_aproveitada=0.0,
                     investimento_min=0.0, investimento_max=0.0):
    """Passo a passo da conta, em frases, usando os números da própria simulação."""
    reducao = segmento["reducao_iot"]
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
    if cobertura > 0:
        pct = round(cobertura * 100)
        passos.append(f"Sensores que vocês já têm: cerca de {pct}% dos pontos. A economia já aproveitada com eles é de "
                      f"cerca de {moeda(economia_ja_aproveitada)} no período. O investimento, o lucro e o ROI abaixo "
                      f"valem só para ampliar o monitoramento aos outros {100 - pct}% dos pontos, com economia "
                      f"estimada de {moeda(economia_potencial - economia_ja_aproveitada)}.")
    passos.append(f"Investimento: estimativa de mercado para o seu tipo de empresa, "
                  f"{faixa_investimento(investimento_min, investimento_max)} no período, só com os sensores "
                  "(pontos a monitorar × custo mensal por ponto × meses). Não é preço da Bzu: o valor final é "
                  "definido na proposta.")
    passos.append("De onde vem a faixa: como a Bzu não divulga preços, ela é uma estimativa de mercado feita com "
                  "preços públicos de fornecedores de sensores (por exemplo Erbessd, Monnit e Mitti), considerando "
                  "o sensor e a instalação diluídos em 36 meses, a assinatura da plataforma e a conectividade. "
                  "Medir temperatura costuma custar menos que medir vibração, por isso cada tipo de empresa tem "
                  "a sua faixa. É uma referência para planejar, não uma cotação.")
    passos.append("Lucro líquido estimado = economia − investimento. ROI estimado = lucro líquido ÷ investimento. "
                  "O lucro e o ROI usam o valor central da faixa.")
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
                    prioridade=None, acompanhamento=None, conexao_local=None, investimento_min=None):
    reducao = segmento["reducao_iot"]

    if roi < 0:
        leitura = (f"Há potencial de economia: a estimativa é evitar cerca de {moeda(economia_bruta)} no período. "
                   "Pelo valor central do investimento estimado, isso ainda não cobre os sensores, mas existem "
                   "caminhos para chegar lá: começar por um piloto nos pontos mais críticos, conferir se o custo "
                   "informado está completo e validar a estimativa com a Bzu.")
        classe = "text-info"
    elif roi < 100:
        leitura = ("O retorno estimado é positivo, mas moderado. Vale começar por um piloto nos pontos "
                   "mais críticos.")
        classe = "text-info"
    else:
        leitura = ("O retorno estimado é alto: a economia estimada é pelo menos o dobro do investimento. "
                   "Vale validar os números com um diagnóstico.")
        classe = "text-success"

    otimista = ""
    if roi < 0 and investimento_min is not None and economia_bruta > investimento_min > 0:
        otimista = (f"No extremo mais econômico da faixa de investimento, a estimativa é de um lucro de cerca de "
                    f"{moeda(economia_bruta - investimento_min)} no período. Uma cotação real pode mudar o resultado.")

    retorno = ""
    if investimento_periodo > 0:
        retorno = (f"A cada R$ 1,00 investido em sensores, a estimativa é evitar "
                   f"R$ {_num(economia_bruta / investimento_periodo)} em perdas.")

    equilibrio = ""
    if investimento_periodo > 0 and perda_total_sem_iot > 0:
        pct = investimento_periodo / perda_total_sem_iot * 100
        if pct >= 100:
            equilibrio = ("Com os valores informados, a perda estimada ainda é menor que o investimento estimado. "
                          "Vale começar por poucos pontos críticos ou revisar o custo informado.")
        else:
            equilibrio = (f"Pela estimativa, os sensores se pagam se as perdas caírem pelo menos {_num(pct, 1)}%.")

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
        "otimista": otimista,
        "tempo_real": TEMPO_REAL,
        "monitorar": segmento["monitorar"],
        "conexao": conexao,
        "caso": segmento["caso"],
        "premissa": (f"Estimativa feita com redução de {round(reducao * 100)}% das perdas, "
                     "uma premissa de referência do simulador. O resultado real depende do seu cenário."),
        "site": SITE_BZU,
        "email": EMAIL_BZU,
        "escopo": ESCOPO,
    }
