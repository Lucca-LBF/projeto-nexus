from django import forms


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
        label="Custo por sensor IoT (R$)",
        max_digits=10,
        decimal_places=2,
        initial=300,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "Ex: 300.00",
        }),
        help_text="Custo de instalação de um sensor IoT por máquina.",
    )