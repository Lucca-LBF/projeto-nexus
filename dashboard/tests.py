"""Testes de unidade do dashboard e do relatório (histórias 3 e 7)."""
from django.test import TestCase
from django.urls import reverse

from simulador.tests import CENARIO_ABAIXO_DO_CUSTO, CENARIO_POSITIVO, simular

from .views import _agrupar, _rotulos_blocos


class DashboardTest(TestCase):

    def test_sem_simulacao_volta_ao_formulario(self):
        resposta = self.client.get(reverse("dashboard_home"))
        self.assertRedirects(resposta, reverse("formulario_simulador"), fetch_redirect_response=False)

    def test_veredito_quando_os_sensores_se_pagam(self):
        simular(self.client, CENARIO_POSITIVO)
        resposta = self.client.get(reverse("dashboard_home"))
        self.assertContains(resposta, "Os sensores se pagam")
        self.assertContains(resposta, "Três cenários para a sua economia")
        self.assertContains(resposta, "Pedir diagnóstico")

    def test_caminhos_quando_a_economia_esta_abaixo_do_custo(self):
        simular(self.client, CENARIO_ABAIXO_DO_CUSTO)
        resposta = self.client.get(reverse("dashboard_home"))
        self.assertContains(resposta, "já cobre")
        self.assertContains(resposta, "Caminhos para chegar a 100%")
        self.assertNotContains(resposta, "R$ -")

    def test_agrupar_nao_multiplica_dias(self):
        # 120 dias em semanas: o total do gráfico é o total do período
        valores = [1.0] * 120
        self.assertEqual(sum(_agrupar(valores, 7)), 120)
        self.assertEqual(_rotulos_blocos(120, 7, "Semana")[-1], "Semana 17 (8 dias)")


class RelatorioTest(TestCase):

    def test_relatorio_tem_resultado_e_contato(self):
        simular(self.client, CENARIO_POSITIVO)
        resposta = self.client.get(reverse("relatorio"))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Como calculamos")
        self.assertContains(resposta, "Pedir diagnóstico")
