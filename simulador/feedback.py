"""Monta o retorno que a empresa recebe junto com o resultado da simulação."""

import math
from urllib.parse import quote

from .segmentos import ACOMPANHAMENTO, CONEXAO_LOCAL, FONTES_INVESTIMENTO

SITE_BZU = "https://bzutech.com.br"
# como cada nível de confiança da fonte aparece para o visitante
NIVEL_EVIDENCIA = {"alta": "evidência forte", "média": "evidência parcial", "baixa": "evidência inicial"}

# contato da Bzu (o mesmo do site deles): o botão "Pedir diagnóstico" abre uma conversa já com a mensagem pronta
WHATSAPP_BZU = "5581992259287"
EMAIL_BZU = "bzu@bzutech.com"

# o investimento é uma faixa de mercado para o tipo de empresa e conta só os sensores: o resto a Bzu define na proposta
ESCOPO = ("")


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


def moeda_estimada(valor):
    """Valor arredondado para não parecer exato; abaixo de R$ 1.000 mostra os centavos (senão vira 'R$ 0')."""
    return moeda(valor) if abs(valor) < 1000 else moeda_inteira(valor)


def faixa_investimento(minimo, maximo, curta=False):
    """Faixa de investimento em texto: 'entre R$ 4.100 e R$ 9.900' (ou 'R$ 4.100 a R$ 9.900', se curta)."""
    if curta:
        return f"{moeda_inteira(minimo)} a {moeda_inteira(maximo)}"
    return f"entre {moeda_inteira(minimo)} e {moeda_inteira(maximo)}"


def faixa_roi(economia, investimento_min, investimento_max):
    """ROI nos dois extremos da faixa de investimento, sem nunca mostrar número negativo.

    'de 12% a 80%' quando os dois extremos são positivos; 'até 80%' quando só o extremo mais econômico
    é positivo; None quando nenhum é (quem chama mostra o que falta para os sensores se pagarem)."""
    if investimento_min <= 0 or investimento_max <= 0:
        return None
    pior = (economia - investimento_max) / investimento_max * 100
    melhor = (economia - investimento_min) / investimento_min * 100
    if melhor <= 0:
        return None
    if pior >= 0:
        return f"de {pior:.0f}% a {melhor:.0f}%"
    return f"até {melhor:.0f}%"


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
        "sugestao": ("Sugestão: ampliar a cobertura para os pontos que vão receber sensores e revisar, "
                     "num diagnóstico, a qualidade dos sensores que já existem."),
    }


def fontes_reducao(segmento):
    """De onde vem o percentual de redução do setor: texto, faixa encontrada, confiança e links."""
    ref = segmento["reducao_ref"]
    minimo, maximo = ref["faixa"]
    percentual = round(segmento["reducao_iot"] * 100)
    confianca = ref["confianca"]
    if confianca == "baixa":
        aviso = "É uma premissa do grupo, apoiada em estudos indiretos. O diagnóstico mede o valor real da sua operação."
    elif confianca == "média":
        aviso = "A evidência é parcial: os estudos tratam do tema em casos próximos ao seu."
    else:
        aviso = "Há estudos publicados com resultados medidos para este tipo de operação."
    dentro = minimo <= percentual <= maximo
    uso = (f"O simulador usa {percentual}%, dentro dessa faixa." if dentro
           else f"O simulador usa {percentual}%, fora dessa faixa.")
    return {
        "percentual": percentual,
        "minimo": minimo,
        "maximo": maximo,
        "faixa": f"de {minimo}% a {maximo}%",
        "confianca": confianca,
        "nivel": NIVEL_EVIDENCIA.get(confianca, confianca),
        "aviso": aviso,
        "base": f"{ref['base'].strip()} {uso}",
        "links": ref["fontes"],
        "investimento": FONTES_INVESTIMENTO,
    }


def faixa_economia(economia, segmento):
    """Economia mínima e máxima se a redução de perdas ficar nos extremos da faixa encontrada nos estudos.

    A economia cresce na mesma proporção da redução (a linha do gráfico de sensibilidade), então basta
    escalar a economia simulada. O lucro e o ROI continuam usando o percentual do simulador."""
    reducao = segmento["reducao_iot"]
    minimo, maximo = segmento["reducao_ref"]["faixa"]
    if reducao <= 0 or economia <= 0:
        return 0.0, 0.0
    return economia * minimo / 100 / reducao, economia * maximo / 100 / reducao


def montar_por_mes(salvo, segmento):
    """Economia, custo dos sensores e saldo por mês (e por ponto), sem nunca mostrar número negativo.

    O custo dos sensores no simulador é mensal (pontos × custo por ponto), não um investimento único:
    por isso não existe um "mês do payback". O que decide se compensa é o saldo de cada mês."""
    economia = salvo.get('economia_mensal', 0.0)
    custo = salvo.get('custo_mensal', 0.0)
    pontos = salvo.get('pontos_novos', 0.0)
    meses = salvo.get('tempo_amostra', 30) / 30
    if custo <= 0:
        return None
    saldo = economia - custo
    if saldo >= 0:
        saldo_titulo, saldo_classe = "Sobra por mês", "text-success"
        saldo_texto = "Economia maior que o custo dos sensores."
    else:
        saldo_titulo, saldo_classe = "Para cobrir 100%", "text-info"
        saldo_texto = "A mais de economia por mês para cobrir o custo dos sensores."
    principal = "Paradas evitadas" if segmento["modelo"] == "paradas" else "Perdas evitadas"
    conserto_mes = salvo.get('economia_conserto_nova', 0.0) / meses if meses > 0 else 0.0
    origem = [(principal, moeda_estimada(max(economia - conserto_mes, 0.0)))]
    if conserto_mes > 0:
        origem.append(("Conserto de emergência evitado", moeda_estimada(conserto_mes)))
    return {
        "economia": moeda_estimada(economia),
        "custo": moeda_estimada(custo),
        "custo_faixa": faixa_investimento(salvo.get('custo_mensal_min', 0.0), salvo.get('custo_mensal_max', 0.0)),
        "saldo_titulo": saldo_titulo,
        "saldo": moeda_estimada(saldo) if saldo >= 0 else f"+ {moeda_estimada(-saldo)}",
        "saldo_classe": saldo_classe,
        "saldo_texto": saldo_texto,
        "economia_ponto": moeda(economia / pontos) if pontos > 0 else None,
        "custo_ponto": moeda(segmento["custo_ponto"]),
        "custo_ponto_faixa": f"{moeda_estimada(segmento['custo_ponto_faixa'][0])} a {moeda_estimada(segmento['custo_ponto_faixa'][1])}",
        "origem": origem,
    }


def explicar_calculo(segmento, dados, regime_texto, fator_regime, dias, economia_conserto,
                     cobertura=0.0, economia_potencial=0.0, economia_ja_aproveitada=0.0,
                     investimento_min=0.0, investimento_max=0.0, horas_dia=None, horas_limitadas=False):
    """Passo a passo da conta, em frases, usando os números da própria simulação."""
    reducao = segmento["reducao_iot"]
    passos = []

    if segmento["modelo"] == "perdas":
        perda_periodo = dados["perda_mensal"] * dias / 30
        passos.append(f"Perda estimada: {moeda(dados['perda_mensal'])} por mês, ou cerca de "
                      f"{moeda(perda_periodo)} em {dias} dias sem sensores.")
    else:
        n = dados["num_maquinas"]
        if horas_dia is None:
            horas_dia = math.sqrt(n) * segmento["taxa_falha_base"] * fator_regime
        texto_horas = (f"Paradas por dia: √{n} (raiz do número de máquinas, porque nem todas param ao mesmo tempo) × "
                       f"{_num(segmento['taxa_falha_base'])} hora de parada por dia × {_num(fator_regime, 1)} "
                       f"({regime_texto})")
        if horas_limitadas:
            texto_horas += (f", limitado a um teto de {_num(horas_dia, 1)} hora(s) por dia para não passar de uma "
                            "fração realista do tempo de funcionamento.")
        else:
            texto_horas += f" = cerca de {_num(horas_dia, 1)} hora(s)."
        passos.append(texto_horas)
        passos.append(f"Cada hora parada custa {moeda(dados['custo_hora_parada'])}, então, sem sensores, as paradas "
                      f"custariam cerca de {moeda(horas_dia * dias * dados['custo_hora_parada'])} em {dias} dias.")

    fonte = fontes_reducao(segmento)
    origem = ("premissa do grupo, apoiada em estudos indiretos"
              if fonte["confianca"] == "baixa"
              else f"estudos publicados indicam {fonte['faixa']} para esse tipo de operação")
    passos.append(f"Com sensores e alertas, a estimativa é evitar {round(reducao * 100)}% dessas perdas "
                  f"({origem}). Veja em \"Fontes dos números\".")
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
                  "(pontos a monitorar × custo mensal por ponto × meses). O valor final é definido na proposta da Bzu.")
    passos.append("De onde vem a faixa: é uma estimativa de mercado feita com "
                  "preços públicos de fornecedores de sensores (por exemplo Erbessd, Monnit e Mitti), considerando "
                  "o sensor e a instalação diluídos em 36 meses, a assinatura da plataforma e a conectividade. "
                  "Medir temperatura costuma custar menos que medir vibração, por isso cada tipo de empresa tem "
                  "a sua faixa. É uma referência para planejar: a cotação vem na proposta.")
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
                    prioridade=None, acompanhamento=None, conexao_local=None, investimento_min=None,
                    falta_pagar=None, meses=None):
    reducao = segmento["reducao_iot"]

    if roi < 0:
        cobre = f"{economia_bruta / investimento_periodo * 100:.0f}%" if investimento_periodo > 0 else "parte"
        leitura = (f"Há potencial de economia: a estimativa é evitar cerca de {moeda(economia_bruta)} no período, "
                   f"o que já cobre {cobre} do custo estimado dos sensores. Caminhos para chegar a 100%: começar "
                   "por um piloto nos pontos mais críticos, conferir se o custo informado está completo e validar "
                   "a estimativa com a Bzu.")
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

    # custo de não agir: o que deixa de ser evitado a cada mês sem monitoramento (antes do custo dos sensores)
    esperar = ""
    if meses and meses > 0 and economia_bruta > 0:
        esperar = (f"Cada mês sem monitoramento, a estimativa é deixar de evitar cerca de "
                   f"{moeda(economia_bruta / meses)} em perdas (antes de descontar o custo dos sensores).")

    equilibrio = ""
    if falta_pagar and roi < 0:
        equilibrio = falta_pagar
    elif investimento_periodo > 0 and perda_total_sem_iot > 0:
        pct = investimento_periodo / perda_total_sem_iot * 100
        if pct >= 100:
            equilibrio = ("Vale começar por poucos pontos críticos, onde a perda é maior, e confirmar o custo "
                          "informado no diagnóstico.")
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
        "esperar": esperar,
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
