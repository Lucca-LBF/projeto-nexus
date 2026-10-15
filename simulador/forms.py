from django import forms

from .segmentos import ACOMPANHAMENTO, CONEXAO_LOCAL, SEGMENTOS, opcoes_prioridade

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


class DadosEmpresaForm(forms.Form):
    """
    Formulário para coletar os dados da empresa, usados pelo
    simulador para calcular a economia estimada com IoT.
    """

    # o tipo da empresa vem primeiro, porque as perguntas seguintes mudam conforme ele
    field_order = [
        "tipo_industria",
        "num_maquinas",
        "custo_hora_parada",
        "perda_mensal",
        "custo_sensor_iot",
        "tempo_amostra",
        "prioridade",
        "acompanhamento_atual",
        "conexao_local",
    ]

    num_maquinas = forms.IntegerField(
        label="Número de máquinas",
        min_value=1,
        initial=100,
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
        min_value=0,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "Ex: 20000.00",
        }),
        help_text="Quanto você estima perder por mês hoje.",
    )

    custo_sensor_iot = forms.DecimalField(
        label="Custo mensal do sensor IoT (R$)",
        max_digits=10,
        decimal_places=2,
        initial=300,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "Ex: 300.00",
        }),
        help_text="Custo mensal de um sensor IoT por máquina.",
    )

    tipo_industria = forms.ChoiceField(
        label="Tipo da empresa",
        choices=TIPO_EMPRESA_CHOICES,
        initial="padrao",
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Muda as perguntas e o perfil usado na simulação.",
    )

    tempo_amostra = forms.TypedChoiceField(
        label="Tempo de análise (dias/mês)",
        choices=TEMPO_ANALISE_CHOICES,
        coerce=int,
        initial=30,
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Período simulado, enviado em dias.",
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
        for nome, textos in dados["campos"].items():
            self.fields[nome].label = textos["label"]
            self.fields[nome].help_text = textos["ajuda"]
