"""
Catálogo de segmentos do simulador.

A chave de cada segmento é o value do select "tipo_industria".
Para criar um segmento novo, basta copiar um bloco abaixo e trocar os textos.

modelo:
  "paradas" -> o usuário informa o custo de uma hora parada (calcula horas x custo)
  "perdas"  -> o usuário informa quanto perde por mês (calcula perda mensal x redução)

prioridades: opções da pergunta "Qual é a sua prioridade?" deste segmento.
  Cada item é (valor, texto da opção, "comece por ..."). A opção escolhida
  aparece no retorno que a empresa recebe junto com o resultado.

custo_ponto: custo mensal estimado por ponto monitorado (R$ por ponto por mês), considerando só os
  sensores: o sensor e a instalação diluídos em 36 meses, mais assinatura e conectividade.
  É o valor central, usado no lucro e no ROI. custo_ponto_faixa é o intervalo (mínimo, máximo) mostrado
  como "investimento estimado". Medir temperatura sai mais barato que medir vibração.
  São estimativas de mercado a partir de preços públicos de fornecedores de IoT (US$ 1 = R$ 5,50),
  não são preço da Bzu, que não publica valores. Troque quando a Bzu informar uma faixa real.

taxa_falha_base e reducao_iot são premissas de referência do simulador.
Os quatro primeiros segmentos mantêm os valores que o grupo já usava; os demais
começam com a premissa do padrão (15%) até a Bzu confirmar valores reais.
"""

# "Não sei o valor": a pessoa informa o gasto mensal e quanto acha que se perde;
# o formulário multiplica e preenche o campo. Percentuais são premissas de referência.
PERCENTUAIS_ESTIMATIVA = [
    (5, "Pouco (cerca de 5%)"),
    (10, "Moderado (cerca de 10%)"),
    (20, "Bastante (cerca de 20%)"),
]

# perguntas iguais para todos os segmentos: (valor, texto da opção, comentário no retorno)
# As de prioridade e conexão só personalizam o retorno. A de acompanhamento também separa
# a economia já aproveitada (pontos que já têm sensores) da que ainda dá para ganhar.
ACOMPANHAMENTO = [
    ("nao", "Não acompanhamos hoje",
     "Hoje vocês não acompanham esses pontos, então qualquer dado em tempo real já é um ganho: "
     "o problema passa a ser visto quando acontece, não depois."),
    ("manual", "Manualmente (rondas, anotações, planilhas)",
     "O acompanhamento manual deixa lacunas entre uma ronda e outra. "
     "Sensores com alerta automático cobrem esse intervalo, inclusive à noite e nos fins de semana."),
    ("alguns", "Já temos sensores em alguns pontos",
     "Como já existem sensores em parte dos pontos, uma parte da economia já está sendo aproveitada. "
     "O caminho é ampliar o monitoramento para os pontos que ainda ficam sem sensor."),
    ("maioria", "Já temos sensores na maior parte dos pontos",
     "Como a maior parte dos pontos já tem sensores, grande parte da economia já está sendo aproveitada. "
     "Um diagnóstico mostra o que falta cobrir e o que dá para melhorar no que já existe."),
]

# Parte dos pontos que já tem sensores em cada resposta. É uma hipótese do simulador:
# serve para separar a economia "já aproveitada" da que ainda dá para ganhar ampliando.
# Respostas antigas guardadas na sessão ("sistema") contam como "alguns".
COBERTURA_SENSORES = {"nao": 0.0, "manual": 0.0, "alguns": 0.3, "sistema": 0.3, "maioria": 0.7}
# texto curto para o resumo dos dados informados
ACOMPANHAMENTO_RESUMO = {
    "nao": "Nenhum sensor", "manual": "Nenhum sensor (acompanhamento manual)",
    "alguns": "Sensores em alguns pontos", "sistema": "Sensores em alguns pontos",
    "maioria": "Sensores na maior parte dos pontos",
}

# Quanto tempo as máquinas funcionam por dia: (valor, texto da opção, fator, texto curto).
# O fator multiplica as horas de parada esperadas por dia. As taxas de falha do catálogo
# foram calibradas para 2 turnos (16 h por dia), então esse é o fator 1.0 e o padrão do formulário.
# Só vale para os segmentos do modelo "paradas": nos de "perdas" a pessoa já informa a perda mensal.
REGIME_PADRAO = "2turnos"
REGIME_FUNCIONAMENTO = [
    ("1turno", "1 turno (cerca de 8 horas por dia)", 0.5, "1 turno"),
    ("2turnos", "2 turnos (cerca de 16 horas por dia)", 1.0, "2 turnos"),
    ("24h", "24 horas por dia", 1.5, "24 horas por dia"),
]

CONEXAO_LOCAL = [
    ("nao_sei", "Não sei informar", None),
    ("wifi", "Temos Wi-Fi estável em todo o local",
     "Como o local tem Wi-Fi estável, os sensores podem usar Wi-Fi, que costuma ser a instalação mais simples."),
    ("parcial", "Temos Wi-Fi só em parte do local",
     "Com Wi-Fi só em parte do local, dá para usar Wi-Fi onde houver sinal e LoRa nas áreas sem cobertura."),
    ("sem", "Não temos rede, ou a área é muito ampla",
     "Sem rede local ou com área ampla, LoRa ou LTE são as opções para levar os dados dos sensores até a nuvem."),
]

SEGMENTOS = {
    "padrao": {
        "rotulo": "Indústria em geral",
        "custo_ponto": 150,
        "custo_ponto_faixa": (90, 220),
        "nome": "Simulação Padrão",
        "modelo": "paradas",
        "taxa_falha_base": 0.04,
        "reducao_iot": 0.15,
        "rotulo_pontos": ("Frota Monitorada", "Máquinas"),
        "intro": "Informe os dados da sua operação para estimar o retorno de investir em sensores IoT.",
        "campos": {
            "num_maquinas": {
                "label": "Quantas máquinas você quer monitorar?",
                "ajuda": "Quantidade total de máquinas que seriam monitoradas.",
            },
            "custo_hora_parada": {
                "label": "Quanto custa uma hora de máquina parada? (R$)",
                "ajuda": "Prejuízo estimado por hora de máquina parada.",
            },
        },
        "monitorar": "Temperatura, vibração e funcionamento das máquinas mais críticas, com alertas automáticos.",
        "conexao": "Wi-Fi onde houver rede estável; LoRa para áreas amplas ou com muitas paredes.",
        "caso": "",
        "prioridades": [
            ("paradas", "Evitar paradas inesperadas",
             "as máquinas que mais interrompem a produção"),
            ("manutencao", "Planejar melhor a manutenção",
             "os equipamentos com mais histórico de falha"),
            ("energia", "Reduzir o consumo de energia",
             "os equipamentos que mais consomem"),
            ("qualidade", "Manter a qualidade do produto",
             "os pontos do processo que mais afetam a qualidade"),
        ],
    },
    "textil": {
        "rotulo": "Indústria têxtil",
        "custo_ponto": 150,
        "custo_ponto_faixa": (90, 220),
        "nome": "Indústria Têxtil",
        "modelo": "paradas",
        "taxa_falha_base": 0.06,
        "reducao_iot": 0.12,
        "rotulo_pontos": ("Frota Monitorada", "Máquinas"),
        "intro": "Informe os dados da sua indústria têxtil para estimar quanto o monitoramento IoT evitaria em paradas de produção.",
        "campos": {
            "num_maquinas": {
                "label": "Quantos teares e máquinas de produção você quer monitorar?",
                "ajuda": "Conte teares, fiadeiras, máquinas de costura e de acabamento que receberiam sensores.",
            },
            "custo_hora_parada": {
                "label": "Quanto você perde por hora com um tear ou uma linha parada? (R$)",
                "ajuda": "Considere a produção perdida, o desperdício de fio e tecido e os atrasos de entrega.",
            },
        },
        "monitorar": "Vibração, temperatura e tempo de funcionamento de teares e máquinas de produção, com alerta antes da parada.",
        "conexao": "Wi-Fi ou LoRa, conforme a cobertura do galpão.",
        "caso": "",
        "prioridades": [
            ("paradas", "Evitar paradas de teares e linhas",
             "os teares e as linhas que mais atrasam entregas"),
            ("desperdicio", "Reduzir desperdício de fio e tecido",
             "as máquinas em que o desperdício é maior"),
            ("manutencao", "Planejar melhor a manutenção",
             "as máquinas com mais histórico de falha"),
            ("energia", "Reduzir o consumo de energia",
             "as máquinas que mais consomem"),
        ],
    },
    "pesada": {
        "rotulo": "Indústria pesada",
        "custo_ponto": 200,
        "custo_ponto_faixa": (130, 320),
        "nome": "Manufatura Pesada",
        "modelo": "paradas",
        "taxa_falha_base": 0.03,
        "reducao_iot": 0.25,
        "rotulo_pontos": ("Frota Monitorada", "Máquinas"),
        "intro": "Informe os dados da sua manufatura pesada para estimar o retorno de monitorar os equipamentos críticos.",
        "campos": {
            "num_maquinas": {
                "label": "Quantas máquinas pesadas (prensas, tornos, fornos) você quer monitorar?",
                "ajuda": "Conte só os equipamentos críticos, aqueles cuja parada interrompe a linha.",
            },
            "custo_hora_parada": {
                "label": "Quanto custa uma hora de linha pesada parada? (R$)",
                "ajuda": "Considere a produção perdida, a equipe ociosa e o custo de reiniciar o equipamento.",
            },
        },
        "monitorar": "Temperatura, vibração e carga dos equipamentos críticos, para antecipar falhas antes que a linha pare.",
        "conexao": "Wi-Fi ou LoRa, conforme a cobertura do galpão.",
        "caso": "",
        "prioridades": [
            ("paradas", "Evitar paradas da linha",
             "os equipamentos cuja parada interrompe toda a linha"),
            ("seguranca", "Aumentar a segurança de equipamentos e equipe",
             "os equipamentos que operam perto do limite de temperatura ou carga"),
            ("manutencao", "Passar da manutenção corretiva para a preventiva",
             "os equipamentos com mais histórico de quebra"),
            ("energia", "Reduzir o consumo de energia",
             "os equipamentos de maior carga"),
        ],
    },
    "refrigeracao": {
        "rotulo": "Cadeia fria e refrigeração",
        "custo_ponto": 90,
        "custo_ponto_faixa": (60, 140),
        "nome": "Frio Industrial e Refrigeração",
        "modelo": "paradas",
        "taxa_falha_base": 0.04,
        "reducao_iot": 0.35,
        "rotulo_pontos": ("Frota Monitorada", "Equipamentos"),
        "intro": "Informe os dados da sua operação de frio industrial para estimar o retorno de monitorar a cadeia do frio.",
        "campos": {
            "num_maquinas": {
                "label": "Quantos compressores, câmaras frias e chillers você quer monitorar?",
                "ajuda": "Conte cada equipamento de refrigeração que receberia um sensor.",
            },
            "custo_hora_parada": {
                "label": "Quanto custa uma hora de refrigeração fora de operação? (R$)",
                "ajuda": "Considere a perda de produtos refrigerados e o risco de quebrar a cadeia do frio.",
            },
        },
        "monitorar": "Temperatura e umidade de câmaras frias, freezers e áreas de armazenamento, com alerta imediato de desvio.",
        "conexao": "Wi-Fi ou LoRa, conforme a cobertura do local.",
        "caso": "LAFEPE: monitoramento de câmaras frias, freezers e áreas de armazenamento.",
        "prioridades": [
            ("produto", "Evitar perda de produto por desvio de temperatura",
             "as câmaras e áreas com produtos mais sensíveis ou de maior valor"),
            ("equipamento", "Evitar quebra de compressores e câmaras",
             "os compressores e as câmaras mais antigos ou com mais chamados"),
            ("energia", "Reduzir o consumo de energia do frio",
             "os equipamentos que ficam mais tempo ligados"),
            ("auditoria", "Ter registro de temperatura para auditoria",
             "as áreas que precisam de histórico para fiscalização"),
        ],
    },
    "alimentos": {
        "rotulo": "Alimentos e bebidas",
        "custo_ponto": 100,
        "custo_ponto_faixa": (60, 140),
        "nome": "Alimentos e Bebidas",
        "modelo": "perdas",
        "taxa_falha_base": None,
        "reducao_iot": 0.15,
        "rotulo_pontos": ("Pontos Monitorados", "Pontos"),
        "intro": "Informe os dados da sua produção de alimentos ou bebidas para estimar quanto o monitoramento do processo evitaria em perdas.",
        "campos": {
            "num_maquinas": {
                "label": "Quantos pontos do processo (tanques, fermentadores, câmaras, linhas) você quer monitorar?",
                "ajuda": "Conte cada ponto em que temperatura ou umidade fora do ideal afeta o produto.",
            },
            "perda_mensal": {
                "label": "Quanto você perde por mês com lotes descartados ou fora do padrão? (R$)",
                "ajuda": "Considere matéria-prima, energia e retrabalho dos lotes perdidos.",
                "estimar": "Quanto vale, por mês, a produção que passa por esses pontos? (R$)",
            },
        },
        "monitorar": "Temperatura, umidade e outras variáveis do processo (como a fermentação), para manter a consistência do produto.",
        "conexao": "Wi-Fi ou LoRa, conforme a cobertura da planta.",
        "caso": "Grupo M. Dias Branco: fermentação na indústria alimentícia, com monitoramento de temperatura, umidade e variáveis do processo.",
        "prioridades": [
            ("lotes", "Reduzir lotes perdidos ou fora do padrão",
             "as etapas em que mais se perde lote"),
            ("consistencia", "Manter a consistência do produto",
             "as etapas sensíveis à temperatura e à umidade, como a fermentação"),
            ("registro", "Ter registro do processo para auditoria",
             "as etapas que exigem histórico de temperatura e umidade"),
            ("energia", "Reduzir o consumo de energia",
             "as câmaras e os equipamentos que mais consomem"),
        ],
    },
    "saude": {
        "rotulo": "Saúde e farmacêutica",
        "custo_ponto": 110,
        "custo_ponto_faixa": (70, 160),
        "nome": "Saúde e Farmacêutica",
        "modelo": "perdas",
        "taxa_falha_base": None,
        "reducao_iot": 0.15,
        "rotulo_pontos": ("Equipamentos Monitorados", "Câmaras e áreas"),
        "intro": "Informe os dados da sua operação de saúde ou farmacêutica para estimar o retorno de monitorar a cadeia fria de medicamentos e insumos.",
        "campos": {
            "num_maquinas": {
                "label": "Quantas câmaras frias, freezers e áreas de armazenamento você quer monitorar?",
                "ajuda": "Conte cada equipamento ou área que guarda medicamentos, vacinas ou insumos sensíveis.",
            },
            "perda_mensal": {
                "label": "Quanto você perde por mês com medicamentos, vacinas ou insumos descartados? (R$)",
                "ajuda": "Considere os itens descartados por desvio de temperatura e o custo de reposição.",
                "estimar": "Quanto você gasta por mês com os medicamentos e insumos guardados nesses locais? (R$)",
            },
        },
        "monitorar": "Temperatura e umidade de câmaras e áreas de armazenamento, com histórico para rastreabilidade e auditoria.",
        "conexao": "Wi-Fi ou LoRa, conforme a cobertura do local.",
        "caso": "LAFEPE: cadeia de frio em câmaras frias, freezers e áreas de armazenamento. Também há um projeto de rastreabilidade de bolsas de plasma.",
        "prioridades": [
            ("temperatura", "Garantir a faixa de temperatura de medicamentos e vacinas",
             "as câmaras com os itens mais sensíveis"),
            ("auditoria", "Ter histórico de temperatura para auditoria",
             "todas as áreas que passam por fiscalização"),
            ("fora_horario", "Ser avisado de desvios fora do expediente",
             "as câmaras que ficam sem ninguém à noite e nos fins de semana"),
            ("descarte", "Reduzir descarte de itens",
             "as áreas em que mais se descarta por desvio de temperatura"),
        ],
    },
    "utilities": {
        "rotulo": "Água, gás e energia",
        "custo_ponto": 110,
        "custo_ponto_faixa": (80, 150),
        "nome": "Água, Gás e Energia",
        "modelo": "perdas",
        "taxa_falha_base": None,
        "reducao_iot": 0.15,
        "rotulo_pontos": ("Pontos Monitorados", "Pontos"),
        "intro": "Informe os dados da sua operação de água, gás ou energia para estimar quanto o monitoramento evitaria em perdas e desperdício.",
        "campos": {
            "num_maquinas": {
                "label": "Quantos pontos de medição (medidores, reservatórios, redes) você quer monitorar?",
                "ajuda": "Conte cada ponto em que você quer acompanhar o consumo em tempo real.",
            },
            "perda_mensal": {
                "label": "Quanto você estima perder por mês com vazamentos e desperdício? (R$)",
                "ajuda": "Some o que se perde em água, gás ou energia por vazamento, falha ou consumo fora do normal.",
                "estimar": "Quanto você gasta por mês com água, gás ou energia nesses pontos? (R$)",
            },
        },
        "monitorar": "Consumo de água, gás e energia em tempo real, para achar vazamentos e desperdícios.",
        "conexao": "LoRa ou LTE, para medidores espalhados e distantes.",
        "caso": "",
        "prioridades": [
            ("vazamentos", "Encontrar vazamentos",
             "os trechos e pontos com mais perda de água ou gás"),
            ("consumo", "Acompanhar o consumo em tempo real",
             "os maiores pontos de consumo"),
            ("falhas", "Detectar falhas antes de virar problema",
             "os reservatórios e equipamentos mais críticos"),
            ("custo", "Reduzir o custo com energia",
             "os pontos de maior consumo de energia"),
        ],
    },
    "edificios": {
        "rotulo": "Edifícios inteligentes",
        "custo_ponto": 90,
        "custo_ponto_faixa": (60, 130),
        "nome": "Edifícios Inteligentes",
        "modelo": "perdas",
        "taxa_falha_base": None,
        "reducao_iot": 0.15,
        "rotulo_pontos": ("Ambientes Monitorados", "Ambientes"),
        "intro": "Informe os dados do seu edifício para estimar quanto o monitoramento evitaria em desperdício de energia e climatização.",
        "campos": {
            "num_maquinas": {
                "label": "Quantos ambientes ou pavimentos você quer monitorar?",
                "ajuda": "Conte salas, andares ou áreas técnicas que receberiam sensores.",
            },
            "perda_mensal": {
                "label": "Quanto você estima desperdiçar por mês com energia e climatização? (R$)",
                "ajuda": "Considere ar-condicionado e iluminação ligados sem necessidade e equipamentos fora de ajuste.",
                "estimar": "Quanto você paga por mês de energia e climatização do edifício? (R$)",
            },
        },
        "monitorar": "Energia, qualidade do ar, temperatura e uso de equipamentos, para ganhar conforto, segurança e eficiência.",
        "conexao": "Wi-Fi ou LoRa, conforme o tamanho do prédio.",
        "caso": "",
        "prioridades": [
            ("energia", "Reduzir o gasto com energia",
             "os andares e as áreas técnicas que mais consomem"),
            ("conforto", "Melhorar conforto e qualidade do ar",
             "as salas e os andares com mais reclamação"),
            ("manutencao", "Planejar melhor a manutenção",
             "os equipamentos de climatização e áreas técnicas"),
            ("uso", "Entender como os ambientes são usados",
             "as áreas com uso mais variável ao longo do dia"),
        ],
    },
    "cidades": {
        "rotulo": "Cidades inteligentes",
        "custo_ponto": 100,
        "custo_ponto_faixa": (60, 140),
        "nome": "Cidades Inteligentes",
        "modelo": "perdas",
        "taxa_falha_base": None,
        "reducao_iot": 0.15,
        "rotulo_pontos": ("Pontos Monitorados", "Pontos"),
        "intro": "Informe os dados da sua cidade ou empreendimento urbano para estimar o retorno de monitorar equipamentos e ambiente.",
        "campos": {
            "num_maquinas": {
                "label": "Quantos pontos urbanos (mobiliário, postes, praças) você quer monitorar?",
                "ajuda": "Conte cada ponto que receberia sensores de temperatura, qualidade do ar ou energia.",
            },
            "perda_mensal": {
                "label": "Quanto você gasta por mês com manutenção corretiva e energia desses pontos? (R$)",
                "ajuda": "Considere deslocamento de equipe, reparos e consumo de energia que poderiam ser evitados.",
                "estimar": "Quanto você gasta por mês, no total, com manutenção e energia desses pontos? (R$)",
            },
        },
        "monitorar": "Temperatura, qualidade do ar, energia e uso de equipamentos em mobiliário urbano e pontos públicos.",
        "conexao": "LoRa ou LTE, para pontos espalhados pela cidade.",
        "caso": "Smartlet: mobiliário urbano no Recife Antigo, com monitoramento de temperatura, qualidade do ar, energia e uso de equipamentos.",
        "prioridades": [
            ("manutencao", "Reduzir manutenção corretiva",
             "os pontos que mais geram chamados"),
            ("energia", "Reduzir o gasto com energia",
             "os pontos de maior consumo"),
            ("ambiente", "Monitorar qualidade do ar e ambiente",
             "as praças e as vias de maior movimento"),
            ("uso", "Entender o uso dos equipamentos urbanos",
             "os equipamentos mais usados pela população"),
        ],
    },
    "agro": {
        "rotulo": "Agronegócio",
        "custo_ponto": 65,
        "custo_ponto_faixa": (40, 100),
        "nome": "Agronegócio",
        "modelo": "perdas",
        "taxa_falha_base": None,
        "reducao_iot": 0.15,
        "rotulo_pontos": ("Áreas Monitoradas", "Áreas"),
        "intro": "Informe os dados da sua operação agrícola para estimar quanto o monitoramento evitaria em perda de produção.",
        "campos": {
            "num_maquinas": {
                "label": "Quantas estufas, silos ou áreas de cultivo você quer monitorar?",
                "ajuda": "Conte cada local em que temperatura e umidade afetam a produção.",
            },
            "perda_mensal": {
                "label": "Quanto você perde por mês com produção estragada ou irrigação mal ajustada? (R$)",
                "ajuda": "Considere colheita perdida, grãos deteriorados e água ou energia gastas sem necessidade.",
                "estimar": "Quanto vale, por mês, a produção dessas áreas? (R$)",
            },
        },
        "monitorar": "Temperatura e umidade em estufas, silos e áreas de produção, com alerta para agir antes da perda.",
        "conexao": "LoRa ou LTE, para áreas amplas e sem rede local.",
        "caso": "",
        "prioridades": [
            ("clima", "Controlar temperatura e umidade",
             "as estufas e as áreas mais sensíveis ao clima"),
            ("armazenagem", "Evitar perda em silos e armazenamento",
             "os silos e os depósitos com maior volume"),
            ("irrigacao", "Ajustar a irrigação",
             "as áreas com maior gasto de água"),
            ("energia", "Reduzir o gasto com energia e água",
             "os pontos de maior consumo"),
        ],
    },
}


# De onde vem o percentual de redução (reducao_iot) de cada segmento. Aparece em "Fontes" no
# resultado e no relatório. confianca: "alta", "média" ou "baixa" (baixa = premissa do grupo, sem
# estudo que meça a perda evitada). Pesquisa completa: reducoes_iot_por_setor_v2.pdf.
_F_MANUT = ("Reliamag: resumo dos estudos de manutenção preditiva (McKinsey, Deloitte, DOE)",
            "https://reliamag.com/maintenance-and-reliability/predictive-maintenance-roi-benchmarks-what-the-studies-show/")
_F_DELOITTE = ("Fabrico: estatísticas de manutenção preditiva (Deloitte)",
               "https://www.fabrico.io/blog/predictive-maintenance-statistics/")
_F_DOE = ("ASHE: guia de operação e manutenção do governo dos EUA (DOE)", "https://www.ashe.org/pdm?page=55")

REDUCAO_REFERENCIAS = {
    "padrao": {
        "faixa": (10, 30), "confianca": "alta",
        "base": ("Estudos de manutenção preditiva indicam queda de 30% a 50% nas paradas em programas maduros "
                 "(McKinsey) e aumento de 10% a 20% na disponibilidade dos equipamentos (Deloitte)."),
        "fontes": [_F_MANUT, _F_DELOITTE],
    },
    "textil": {
        "faixa": (8, 25), "confianca": "média",
        "base": ("Para o setor têxtil, a referência é a faixa dos estudos da indústria em geral."),
        "fontes": [_F_MANUT, _F_DELOITTE],
    },
    "pesada": {
        "faixa": (15, 40), "confianca": "alta",
        "base": ("Em máquinas críticas o ganho tende a ser maior: a McKinsey cita queda de 30% a 50% nas paradas e "
                 "o guia do governo dos EUA (DOE) cita 35% a 45%."),
        "fontes": [_F_MANUT, _F_DOE],
    },
    "refrigeracao": {
        "faixa": (15, 40), "confianca": "baixa",
        "base": ("A referência de campo mais próxima é a queda de "
                 "25% nos vazamentos de refrigerante em 100 lojas (dado de fornecedor), e uma revisão cita que mais de "
                 "75% dos incidentes de temperatura na cadeia fria farmacêutica seriam evitáveis. "
                 "O diagnóstico mede a perda de produto evitada na sua operação. "),
        "fontes": [("Copeland: programa de detecção de vazamentos em 100 lojas",
                    "https://e360blog.copeland.com/leak-detection-program-shrinks-grocers-carbon-footprint-and-grows-its-bottom-line/"),
                   ("Revisão sobre IoT e inteligência artificial na cadeia fria (PubMed Central)",
                    "https://pmc.ncbi.nlm.nih.gov/articles/PMC12910151/")],
    },
    "alimentos": {
        "faixa": (10, 25), "confianca": "baixa",
        "base": ("Há números do tamanho do problema (supermercados brasileiros perdem cerca de R$ 3,9 bilhões por ano "
                 "em hortifrúti e perecíveis, segundo a ABRAS, com dados de 2017). O diagnóstico mede o efeito do "
                 "monitoramento na sua operação."),
        "fontes": [("IHU Unisinos: ABRAS e o desperdício nos supermercados",
                    "https://ihu.unisinos.br/581949-supermercados-desperdicam-r-3-9-bi-em-alimentos-por-ano-diz-abras")],
    },
    "saude": {
        "faixa": (10, 30), "confianca": "baixa",
        "base": ("Uma meta-análise indica que 14% a 35% das vacinas entregues ficam expostas a temperatura inadequada, "
                 "e um estudo em uma rede hospitalar mostrou que o monitoramento automático detecta desvios que a "
                 "checagem manual deixa passar. O diagnóstico mede a perda evitada na sua operação."),
        "fontes": [("NIST: monitoramento de temperatura na cadeia fria",
                    "https://www.nist.gov/document/nic45-cold-chain-management-temperature-monitoring-solutionspdf"),
                   ("ACHSM: monitoramento automático em uma rede hospitalar",
                    "https://journal.achsm.org.au/index.php/achsm/article/view/899")],
    },
    "utilities": {
        "faixa": (10, 25), "confianca": "baixa",
        "base": ("As perdas não técnicas são grande parte das perdas das distribuidoras brasileiras (ANEEL, 2022), "
                 "o que mostra o tamanho do espaço para reduzir com sensores."),
        "fontes": [("FGV IBRE: perdas de eletricidade no Brasil",
                    "https://blogdoibre.fgv.br/posts/como-evitar-insanidade-nas-perdas-de-eletricidade")],
    },
    "edificios": {
        "faixa": (3, 25), "confianca": "alta",
        "base": ("Na maior amostra publicada (5.900 edifícios), a economia mediana de energia foi de 3% com sistemas de "
                 "informação e de 9% com detecção automática de falhas; a automação predial chega a 10% a 25%. "),
        "fontes": [("Relatório da campanha de análise de energia em edifícios (EMIS)",
                    "https://smartenergyanalytics.org/assets/EMIS%20Report.pdf"),
                   ("ACEEE: tecnologia inteligente em edifícios existentes",
                    "https://www.aceee.org/sites/default/files/publications/researchreports/a1701.pdf")],
    },
    "cidades": {
        "faixa": (10, 35), "confianca": "média",
        "base": ("Dublin reduziu os vazamentos de água em 29% e o Banco Mundial considera realista cortar pela metade a "
                 "água não faturada em países em desenvolvimento (meta de programa completo). A iluminação pública "
                 "adaptativa chega a cerca de 35% em simulação."),
        "fontes": [("Banco Mundial: como reduzir a água não faturada",
                    "https://documents1.worldbank.org/curated/en/385761468330326484/pdf/394050Reducing1e0water0WSS81PUBLIC1.pdf"),
                   ("Economia de energia em iluminação pública adaptativa (simulação)",
                    "https://merit.url.edu/ca/publications/estimating-energy-savings-in-smart-street-lighting-by-using-an-ad/")],
    },
    "agro": {
        "faixa": (10, 40), "confianca": "média",
        "base": ("A irrigação guiada por sensor de umidade economizou de 20% a 42% de água em um ensaio com alface e de "
                 "10% a 64% em outros estudos citados no mesmo artigo. A água é só parte do custo da operação."),
        "fontes": [("Irrigation Science (2025): irrigação com sensores de umidade",
                    "https://link.springer.com/article/10.1007/s00271-024-00969-9")],
    },
}
for _chave, _ref in REDUCAO_REFERENCIAS.items():
    SEGMENTOS[_chave]["reducao_ref"] = _ref

# onde estão os preços usados para a faixa de investimento (custo_ponto_faixa)
FONTES_INVESTIMENTO = [
    ("Erbessd: sistemas de monitoramento de vibração e preços", "https://www.erbessd-instruments.com/en/articles/best-vibration-monitoring-systems/"),
    ("Monnit: monitoramento de cadeia fria", "https://www.monnit.com/temperature-monitoring/cold-chain"),
    ("Mitti: monitoramento de temperatura", "https://mitti.com/apps/temperature-monitoring-solutions"),
    ("OXMaint: custos de sensores sem fio", "https://oxmaint.com/blog/post/wireless-predictive-maintenance-cost-pricing-roi"),
]


def opcoes_prioridade(chave):
    """Opções do select "prioridade" de um segmento: [(valor, texto), ...]."""
    dados = SEGMENTOS.get(chave, SEGMENTOS["padrao"])
    return [(valor, texto) for valor, texto, _ in dados["prioridades"]]


def segmentos_para_formulario():
    """Só o que o navegador precisa para trocar as perguntas."""
    return {
        chave: {
            "modelo": dados["modelo"],
            "intro": dados["intro"],
            "monitorar": dados["monitorar"],
            "campos": dados["campos"],
            "prioridades": [{"valor": v, "texto": t} for v, t in opcoes_prioridade(chave)],
        }
        for chave, dados in SEGMENTOS.items()
    }
