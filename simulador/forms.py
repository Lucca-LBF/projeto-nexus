from decimal import Decimal

from django import forms

from .segmentos import (ACOMPANHAMENTO, CONEXAO_LOCAL, REGIME_FUNCIONAMENTO, REGIME_PADRAO,
                        SEGMENTOS, opcoes_prioridade)

# as opções do select vêm do catálogo de segmentos (segmentos.py)
TIPO_EMPRESA_CHOICES = [(chave, dados["rotulo"]) for chave, dados in SEGMENTOS.items()]

# o valor enviado é o número de dias
TEMPO_ANALISE_CHOICES = [
    (30, "30 dias (1 mês)"),
    (60, "60 dias (2 meses)"),
    (90, "90 dias (3 meses)"),
    (120, "120 dias (4 meses)"),
    (180, "180 dias (6 meses)"),
    (360, "360 dias (12 meses)"),
]


# limites aceitos pelo servidor (o navegador também os usa, mas só o servidor vale)
MAX_PONTOS = 10000
MAX_CUSTO_HORA = Decimal("10000000")
MAX_PERDA_MENSAL = Decimal("100000000")
MAX_CONSERTO_MENSAL = Decimal("100000000")
MAX_CUSTO_SENSOR = Decimal("100000")


def _reais(valor):
    """Decimal('10000000') -> 'R$ 10.000.000,00' (formato brasileiro)."""
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def _mensagens(maximo, positivo=True):
    """Mensagens de erro em português para um campo de valor em reais."""
    mensagens = {
        "required": "Preencha este campo.",
        "invalid": "Digite um número válido, por exemplo 1500 ou 1500.50.",
        "max_value": f"O valor máximo aceito é {_reais(maximo)}.",
        "max_digits": "Número grande demais. Confira os zeros.",
        "max_decimal_places": "Use no máximo 2 casas depois da vírgula.",
        "max_whole_digits": "Número grande demais. Confira os zeros.",
    }
    if positivo:
        mensagens["min_value"] = "Informe um valor maior que zero."
    else:
        mensagens["min_value"] = "O valor não pode ser negativo."
    return mensagens


class DadosEmpresaForm(forms.Form):
    """
    Formulário para coletar os dados da empresa, usados pelo
    simulador para calcular a economia estimada com IoT.
    """

    # o tipo da empresa vem primeiro, porque as perguntas seguintes mudam conforme ele
    field_order = [
        "tipo_industria",
        "num_maquinas",
        "regime_funcionamento",
        "custo_hora_parada",
        "perda_mensal",
        "conserto_mensal",
        "custo_sensor_iot",
        "tempo_amostra",
        "prioridade",
        "acompanhamento_atual",
        "conexao_local",
    ]

    num_maquinas = forms.IntegerField(
        label="Número de máquinas",
        min_value=1,
        max_value=MAX_PONTOS,
        initial=100,
        error_messages={
            "required": "Preencha este campo.",
            "invalid": "Digite um número inteiro, sem vírgula.",
            "min_value": "Informe pelo menos 1.",
            "max_value": f"O máximo aceito é {MAX_PONTOS:,}.".replace(",", "."),
        },
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "Ex: 100",
        }),
        help_text="Quantidade total de máquinas que seriam monitoradas.",
    )

    # cada segmento usa só um destes dois: custo_hora_parada ou perda_mensal
    custo_hora_parada = forms.DecimalField(
        label="Custo por hora de máquina parada (R$)",
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
        max_value=MAX_CUSTO_HORA,
        error_messages=_mensagens(MAX_CUSTO_HORA),
        initial=5000,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "Ex: 5000.00",
        }),
        help_text="Prejuízo estimado por hora de máquina parada.",
    )

    perda_mensal = forms.DecimalField(
        label="Perda mensal estimada (R$)",
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        max_value=MAX_PERDA_MENSAL,
        error_messages=_mensagens(MAX_PERDA_MENSAL),
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "Ex: 20000.00",
        }),
        help_text="Quanto você estima perder por mês hoje.",
    )

    # quanto as máquinas funcionam por dia: muda as horas de parada esperadas (só segmentos de "paradas")
    regime_funcionamento = forms.ChoiceField(
        label="Quanto tempo as máquinas funcionam por dia?",
        choices=[(valor, texto) for valor, texto, _, _ in REGIME_FUNCIONAMENTO],
        initial=REGIME_PADRAO,
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Quanto mais horas ligadas, mais paradas em potencial para evitar.",
    )

    # opcional: se ficar em branco, não entra na conta
    conserto_mensal = forms.DecimalField(
        label="Quanto gasta por mês com conserto de emergência? (R$)",
        required=False,
        max_digits=12,
        decimal_places=2,
        min_value=0,
        max_value=MAX_CONSERTO_MENSAL,
        error_messages=_mensagens(MAX_CONSERTO_MENSAL, positivo=False),
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "Opcional. Ex: 8000.00",
        }),
        help_text="Peças, mão de obra e hora extra de reparos feitos às pressas depois que algo quebra. "
                  "Se não souber, deixe em branco: não entra na conta.",
    )

    custo_sensor_iot = forms.DecimalField(
        label="Custo mensal do sensor IoT (R$)",
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
        max_value=MAX_CUSTO_SENSOR,
        error_messages=_mensagens(MAX_CUSTO_SENSOR),
        initial=300,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "Ex: 300.00",
        }),
        help_text="Custo mensal de um sensor IoT por máquina.",
    )

    tipo_industria = forms.ChoiceField(
        label="Qual é o tipo da sua empresa?",
        choices=TIPO_EMPRESA_CHOICES,
        initial="padrao",
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="As próximas perguntas se adaptam ao seu setor.",
    )

    tempo_amostra = forms.TypedChoiceField(
        label="Por quanto tempo você quer simular?",
        choices=TEMPO_ANALISE_CHOICES,
        coerce=int,
        initial=30,
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Escolha o período da projeção do retorno.",
    )

    # as três perguntas abaixo não entram na conta do ROI: servem para personalizar o retorno
    prioridade = forms.ChoiceField(
        label="Qual é a sua principal prioridade?",
        choices=[],  # as opções vêm do segmento, no __init__
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Usamos para indicar por onde começar.",
    )

    acompanhamento_atual = forms.ChoiceField(
        label="Como vocês acompanham esses pontos hoje?",
        choices=[(valor, texto) for valor, texto, _ in ACOMPANHAMENTO],
        initial="manual",
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Ajuda a entender o quanto os sensores acrescentam ao que já existe.",
    )

    conexao_local = forms.ChoiceField(
        label="Como é a conexão de internet no local?",
        choices=[(valor, texto) for valor, texto, _ in CONEXAO_LOCAL],
        initial="nao_sei",
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Define se os sensores usam Wi-Fi, LoRa ou LTE.",
    )

    def __init__(self, *args, segmento=None, **kwargs):
        super().__init__(*args, **kwargs)
        if segmento not in SEGMENTOS:
            segmento = "padrao"
        dados = SEGMENTOS[segmento]
        self.segmento = segmento
        self.intro = dados["intro"]
        self.monitorar = dados["monitorar"]
        self.fields["prioridade"].choices = opcoes_prioridade(segmento)
        # o campo que o segmento não usa fica desligado (e escondido na tela)
        for nome in ("custo_hora_parada", "perda_mensal"):
            self.fields[nome].disabled = nome not in dados["campos"]
        # o regime de funcionamento só muda a conta nos segmentos de paradas
        self.fields["regime_funcionamento"].disabled = dados["modelo"] != "paradas"
        # na validação, campo desligado não é obrigatório (o navegador não o envia).
        # Sem dados enviados (tela inicial) nada muda, para o HTML manter o "required".
        if self.is_bound:
            for campo in self.fields.values():
                if campo.disabled:
                    campo.required = False
        for nome, textos in dados["campos"].items():
            self.fields[nome].label = textos["label"]
            self.fields[nome].help_text = textos["ajuda"]

    def full_clean(self):
        super().full_clean()
        # campos com erro ficam com a borda vermelha do Bootstrap
        for nome in self.errors:
            if nome in self.fields:
                attrs = self.fields[nome].widget.attrs
                attrs["class"] = (attrs.get("class", "") + " is-invalid").strip()
