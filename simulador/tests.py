"""Testes de unidade do simulador: formulário, cálculo, resultado e contato.

Rodam com `python manage.py test --exclude-tag e2e` (sem navegador).
"""
from django.test import TestCase
from django.urls import reverse

from .feedback import faixa_roi
from .forms import DadosEmpresaForm
from .models import MensagemContato

# um cenário em que os sensores se pagam e outro em que a economia ainda fica abaixo do custo
CENARIO_POSITIVO = {
    "tipo_industria": "pesada", "num_maquinas": "30", "regime_funcionamento": "2turnos",
    "custo_hora_parada": "12000", "conserto_mensal": "4000", "tempo_amostra": "180",
    "prioridade": "paradas", "acompanhamento_atual": "nao", "conexao_local": "wifi",
}
CENARIO_ABAIXO_DO_CUSTO = {
    "tipo_industria": "padrao", "num_maquinas": "60", "regime_funcionamento": "1turno",
    "custo_hora_parada": "10", "conserto_mensal": "", "tempo_amostra": "90",
    "prioridade": "paradas", "acompanhamento_atual": "nao", "conexao_local": "wifi",
}


def simular(client, dados):
    """Envia o formulário e devolve a simulação guardada na sessão."""
    resposta = client.post(reverse("resultado_simulacao"), dados)
    return resposta, client.session.get("simulacao")


class FormularioTest(TestCase):
    """História 1: coleta de dados do cenário operacional."""

    def test_aceita_um_cenario_valido(self):
        form = DadosEmpresaForm(data=CENARIO_POSITIVO, segmento="pesada")
        self.assertTrue(form.is_valid(), form.errors)

    def test_recusa_zero_maquinas(self):
        dados = dict(CENARIO_POSITIVO, num_maquinas="0")
        form = DadosEmpresaForm(data=dados, segmento="pesada")
        self.assertFalse(form.is_valid())
        self.assertIn("num_maquinas", form.errors)

    def test_recusa_valor_negativo(self):
        dados = dict(CENARIO_POSITIVO, custo_hora_parada="-50")
        form = DadosEmpresaForm(data=dados, segmento="pesada")
        self.assertFalse(form.is_valid())
        self.assertIn("custo_hora_parada", form.errors)

    def test_nao_pergunta_o_preco_do_sensor(self):
        form = DadosEmpresaForm(segmento="pesada")
        self.assertFalse(any("sensor" in nome and "custo" in nome for nome in form.fields))


class CalculoTest(TestCase):
    """História 2: cálculo de ROI e viabilidade."""

    def test_cenario_positivo_tem_lucro_e_roi(self):
        resposta, simulacao = simular(self.client, CENARIO_POSITIVO)
        self.assertEqual(resposta.status_code, 200)
        self.assertGreater(simulacao["economia_bruta"], 0)
        self.assertGreater(simulacao["resultado_liquido"], 0)
        self.assertContains(resposta, "Retorno sobre Investimento (ROI) estimado")

    def test_mesmos_dados_mesmo_resultado(self):
        _, primeira = simular(self.client, CENARIO_POSITIVO)
        _, segunda = simular(self.client, CENARIO_POSITIVO)
        self.assertEqual(primeira["economia_bruta"], segunda["economia_bruta"])

    def test_investimento_em_faixa(self):
        _, simulacao = simular(self.client, CENARIO_POSITIVO)
        self.assertLess(simulacao["investimento_min"], simulacao["investimento_periodo"])
        self.assertLess(simulacao["investimento_periodo"], simulacao["investimento_max"])

    def test_resultado_abaixo_do_custo_nao_mostra_numero_negativo(self):
        resposta, simulacao = simular(self.client, CENARIO_ABAIXO_DO_CUSTO)
        self.assertLess(simulacao["resultado_liquido"], 0)
        self.assertContains(resposta, "Para os sensores se pagarem")
        self.assertNotContains(resposta, "R$ -")
        self.assertNotContains(resposta, "-%")

    def test_faixa_do_roi_nunca_negativa(self):
        self.assertIsNone(faixa_roi(100, 500, 900))
        self.assertEqual(faixa_roi(1000, 500, 900), "de 11% a 100%")
        self.assertTrue(faixa_roi(800, 500, 900).startswith("até"))

    def test_resultado_sem_simulacao_volta_ao_formulario(self):
        resposta = self.client.get(reverse("resultado_simulacao"))
        self.assertRedirects(resposta, reverse("formulario_simulador"), fetch_redirect_response=False)


class ContatoTest(TestCase):
    """Histórias 5 e 6: contato, leads e feedback."""

    def test_mensagem_fica_salva(self):
        resposta = self.client.post(reverse("contato"), {
            "nome": "Ana", "email": "ana@empresa.com", "assunto": "comercial", "mensagem": "Quero uma proposta.",
        })
        self.assertContains(resposta, "Mensagem Enviada!")
        self.assertEqual(MensagemContato.objects.get().assunto, "comercial")

    def test_formulario_tem_opcao_de_feedback(self):
        resposta = self.client.get(reverse("contato"))
        self.assertContains(resposta, 'value="feedback"')
