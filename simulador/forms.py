from django import forms
 
TIPO_EMPRESA_CHOICES = [
    ("padrao", "Padrão"),
    ("textil", "Têxtil"),
    ("pesada", "Pesada"),
    ("refrigeracao", "Refrigeração"),
]
 
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
        help_text="Define o perfil de paradas usado na simulação.",
    )
 
    tempo_amostra = forms.TypedChoiceField(
        label="Tempo de análise (dias/mês)",
        choices=TEMPO_ANALISE_CHOICES,
        coerce=int,
        initial=30,
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Período simulado, enviado em dias.",
    )