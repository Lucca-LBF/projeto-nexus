"""Testes de sistema (E2E) das histórias de usuário, com Selenium e Chrome sem janela (headless).

Cada teste abre o site num servidor de teste do Django e usa as telas como um visitante:
clica nos botões, responde o formulário passo a passo e confere o que aparece.

Rodar só estes testes:  python manage.py test --tag e2e
Ver o navegador abrindo: E2E_MOSTRAR=1 python manage.py test --tag e2e
Ao fim de cada teste, um print da tela fica em e2e/prints/ (o pipeline guarda essa pasta).
"""
import os
from pathlib import Path

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import tag
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from simulador.models import MensagemContato

PASTA_PRINTS = Path(__file__).resolve().parent / "prints"
ESPERA = 20  # segundos

# respostas do formulário: os dois cenários das histórias 2 e 3
CENARIO_POSITIVO = {
    "tipo_industria": "pesada", "num_maquinas": "30", "regime_funcionamento": "2turnos",
    "custo_hora_parada": "12000", "conserto_mensal": "4000", "tempo_amostra": "180",
    "acompanhamento_atual": "nao", "conexao_local": "wifi",
}
CENARIO_ABAIXO_DO_CUSTO = {
    "tipo_industria": "padrao", "num_maquinas": "60", "regime_funcionamento": "1turno",
    "custo_hora_parada": "10", "conserto_mensal": "", "tempo_amostra": "90",
    "acompanhamento_atual": "nao", "conexao_local": "wifi",
}


def criar_navegador():
    """Chrome headless. No GitHub Actions o Chrome e o driver já vêm instalados."""
    opcoes = webdriver.ChromeOptions()
    if not os.environ.get("E2E_MOSTRAR"):
        opcoes.add_argument("--headless=new")
    for argumento in ("--no-sandbox", "--disable-dev-shm-usage", "--window-size=1366,900", "--lang=pt-BR",
                      # sem rolagem suave nem animações: o teste não clica num botão ainda em movimento
                      "--force-prefers-reduced-motion"):
        opcoes.add_argument(argumento)
    # não espera fontes e bibliotecas externas (CDN) para começar a testar
    opcoes.page_load_strategy = "eager"
    if os.environ.get("CHROME_BIN"):
        opcoes.binary_location = os.environ["CHROME_BIN"]
    servico = Service(os.environ["CHROMEDRIVER"]) if os.environ.get("CHROMEDRIVER") else Service()
    return webdriver.Chrome(options=opcoes, service=servico)


@tag("e2e")
class HistoriasE2E(StaticLiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.navegador = criar_navegador()
        cls.navegador.implicitly_wait(0)

    @classmethod
    def tearDownClass(cls):
        cls.navegador.quit()
        super().tearDownClass()

    def setUp(self):
        # cada teste começa sem simulação guardada
        self.navegador.delete_all_cookies()
        self.addCleanup(self.guardar_print)

    # ---------- ajudantes ----------

    def guardar_print(self):
        PASTA_PRINTS.mkdir(exist_ok=True)
        self.navegador.save_screenshot(str(PASTA_PRINTS / f"{self._testMethodName}.png"))

    def abrir(self, caminho):
        self.navegador.get(self.live_server_url + caminho)

    def esperar(self, condicao, tempo=ESPERA):
        # enquanto a página troca, um elemento lido pode sumir: só tenta de novo
        return WebDriverWait(self.navegador, tempo, ignored_exceptions=[StaleElementReferenceException]).until(condicao)

    def texto_da_pagina(self):
        """Texto visível da página em minúsculas: o CSS deixa alguns títulos em MAIÚSCULAS."""
        return self.navegador.find_element(By.TAG_NAME, "body").text.lower()

    def esperar_texto(self, texto, tempo=ESPERA):
        self.esperar(lambda navegador: texto.lower() in self.texto_da_pagina(), tempo)

    def rolar_e_clicar(self, elemento):
        """Leva o elemento para o meio da tela na hora (sem rolagem suave) e clica."""
        self.navegador.execute_script(
            "arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", elemento)
        self.esperar(EC.element_to_be_clickable(elemento)).click()

    def clicar_link(self, texto):
        self.rolar_e_clicar(self.esperar(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, texto))))

    def pergunta_atual(self):
        passo = self.esperar(EC.presence_of_element_located((By.CSS_SELECTOR, ".wiz-passo.ativo")))
        return passo, passo.get_attribute("data-campo")

    def esperar_proxima_pergunta(self, campo_anterior):
        def mudou(navegador):
            if "/resultado/" in navegador.current_url:
                return True
            ativos = navegador.find_elements(By.CSS_SELECTOR, ".wiz-passo.ativo")
            return bool(ativos) and ativos[0].get_attribute("data-campo") != campo_anterior
        self.esperar(mudou)

    def responder_formulario(self, respostas):
        """Responde o formulário uma pergunta por vez, como uma pessoa faria, até abrir o resultado."""
        self.abrir("/simulador/?nova=1")
        for _ in range(15):
            if "/resultado/" in self.navegador.current_url:
                return
            passo, campo = self.pergunta_atual()
            selects = passo.find_elements(By.CSS_SELECTOR, ".wiz-resposta select")
            if selects:
                # perguntas de escolha: clica no botão da opção (a escolha já avança)
                indice = self.navegador.execute_script(
                    "var s = arguments[0], v = arguments[1];"
                    "for (var i = 0; i < s.options.length; i++) { if (s.options[i].value === v) return i; }"
                    "return s.selectedIndex;", selects[0], respostas.get(campo, ""))
                opcoes = self.esperar(lambda n: passo.find_elements(By.CSS_SELECTOR, ".wiz-opcao") or False)
                opcoes[indice].click()
            else:
                caixa = passo.find_element(By.CSS_SELECTOR, ".wiz-resposta input")
                caixa.clear()
                if respostas.get(campo):
                    caixa.send_keys(respostas[campo])
                self.navegador.find_element(By.ID, "wiz-continuar").click()
            self.esperar_proxima_pergunta(campo)
        # depois da última pergunta vem a tela de carregamento e o resultado
        self.esperar(EC.url_contains("/resultado/"))

    # ---------- História 4: proposta de valor e navegação ----------

    def test_h4_pagina_inicial_leva_ao_simulador(self):
        self.abrir("/")
        self.clicar_link("Descobrir minha economia")
        self.esperar(EC.url_contains("/simulador/"))
        self.esperar_texto("Qual é o tipo da sua empresa?")

    def test_h4_pagina_inicial_leva_ao_contato(self):
        self.abrir("/")
        self.clicar_link("Tirar uma dúvida")
        self.esperar(EC.url_contains("/contato/"))
        self.esperar(EC.presence_of_element_located((By.ID, "mensagem")))

    def test_h4_menu_aparece_em_todas_as_paginas(self):
        for caminho in ("/", "/simulador/", "/contato/"):
            self.abrir(caminho)
            menu = self.esperar(EC.presence_of_element_located((By.TAG_NAME, "nav")))
            # o CSS do menu deixa os itens em maiúsculas
            for item in ("Início", "Simulador", "Contato"):
                self.assertIn(item.lower(), menu.text.lower(), f"'{item}' no menu de {caminho}")

    # ---------- Histórias 5 e 6: contato, leads e feedback ----------

    def preencher_contato(self, assunto, email="ana@empresa.com"):
        self.abrir("/contato/")
        self.esperar(EC.presence_of_element_located((By.ID, "nome"))).send_keys("Ana Souza")
        if email:
            self.navegador.find_element(By.ID, "email").send_keys(email)
        Select(self.navegador.find_element(By.ID, "assunto")).select_by_value(assunto)
        self.navegador.find_element(By.ID, "mensagem").send_keys("Mensagem enviada pelo teste automatizado.")
        self.rolar_e_clicar(self.navegador.find_element(By.CSS_SELECTOR, "form button[type=submit]"))

    def test_h5_envia_proposta_comercial(self):
        self.preencher_contato("comercial")
        self.esperar_texto("Mensagem Enviada!")
        self.assertEqual(MensagemContato.objects.filter(assunto="comercial").count(), 1)

    def test_h5_campo_obrigatorio_vazio_nao_envia(self):
        self.preencher_contato("duvida", email="")
        email = self.navegador.find_element(By.ID, "email")
        self.assertFalse(self.navegador.execute_script("return arguments[0].checkValidity();", email))
        self.assertEqual(MensagemContato.objects.count(), 0)

    def test_h6_envia_feedback_sem_login(self):
        self.preencher_contato("feedback")
        self.esperar_texto("Mensagem Enviada!")
        self.assertEqual(MensagemContato.objects.filter(assunto="feedback").count(), 1)

    # ---------- Histórias 1 e 2: formulário e cálculo do ROI ----------

    def test_h1_valor_invalido_nao_avanca(self):
        self.abrir("/simulador/?nova=1")
        passo, campo = self.pergunta_atual()
        passo.find_elements(By.CSS_SELECTOR, ".wiz-opcao")[0].click()  # primeiro tipo de empresa
        self.esperar_proxima_pergunta(campo)
        passo, campo = self.pergunta_atual()
        self.assertEqual(campo, "num_maquinas")
        caixa = passo.find_element(By.CSS_SELECTOR, "input")
        caixa.clear()
        caixa.send_keys("0")
        self.navegador.find_element(By.ID, "wiz-continuar").click()
        self.esperar_texto("Informe pelo menos 1.")
        self.assertEqual(self.pergunta_atual()[1], "num_maquinas")

    def test_h1_h2_simulacao_que_se_paga(self):
        self.responder_formulario(CENARIO_POSITIVO)
        self.esperar_texto("Retorno sobre Investimento (ROI) estimado")
        corpo = self.texto_da_pagina()
        self.assertIn("investimento estimado", corpo)
        self.assertNotIn("r$ -", corpo)

    def test_h2_simulacao_abaixo_do_custo_sem_numero_negativo(self):
        self.responder_formulario(CENARIO_ABAIXO_DO_CUSTO)
        self.esperar_texto("Para os sensores se pagarem")
        corpo = self.texto_da_pagina()
        self.assertNotIn("r$ -", corpo)
        self.assertNotIn("-%", corpo)

    # ---------- História 3: dashboard ----------

    def test_h3_dashboard_sem_simulacao_volta_ao_formulario(self):
        self.abrir("/dashboard/")
        self.esperar(EC.url_contains("/simulador/"))

    def test_h3_dashboard_mostra_veredito_e_cenarios(self):
        self.responder_formulario(CENARIO_POSITIVO)
        self.clicar_link("Dashboard")
        self.esperar(EC.url_contains("/dashboard/"))
        self.esperar_texto("Os sensores se pagam")
        corpo = self.texto_da_pagina()
        for trecho in ("Mês a mês", "Três cenários para a sua economia", "Quanto as perdas precisam cair"):
            self.assertIn(trecho.lower(), corpo)

    # ---------- História 7: relatório em PDF ----------

    def test_h7_relatorio_para_salvar_em_pdf(self):
        self.responder_formulario(CENARIO_POSITIVO)
        link = self.esperar(EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, "Baixar relatório")))
        self.assertIn("imprimir=1", link.get_attribute("href"))
        # abre o relatório sem disparar a janela de impressão
        self.abrir("/dashboard/relatorio/")
        self.esperar_texto("Como calculamos")
        self.assertIn("pedir diagnóstico", self.texto_da_pagina())
