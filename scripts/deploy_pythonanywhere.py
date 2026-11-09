"""Deploy contínuo no PythonAnywhere, chamado pelo GitHub Actions depois que todos os testes passam.

O que faz:
1. Descobre quais arquivos mudaram desde o último deploy (o commit anterior do push).
2. Envia esses arquivos para a pasta do projeto no PythonAnywhere, pela API de arquivos,
   e apaga lá os que foram apagados no repositório. Arquivos de static/ também vão para staticfiles/.
3. Recarrega o site pela API (reload do web app).
4. Abre o site e confere se ele respondeu.

Funciona na conta gratuita do PythonAnywhere (não precisa de SSH). Usa só a biblioteca padrão do Python.

Variáveis (configuradas como secrets no GitHub):
  PA_API_TOKEN    token da API (PythonAnywhere > Account > API token)       obrigatório
  PA_USERNAME     usuário do PythonAnywhere (ex.: lucca)                     padrão: o início do PA_DOMAIN
  PA_DOMAIN       endereço do site (ex.: lucca.pythonanywhere.com)           padrão: <PA_USERNAME>.pythonanywhere.com
  PA_PROJECT_DIR  pasta do projeto lá (ex.: /home/lucca/projeto-nexus)       padrão: /home/<PA_USERNAME>/projeto-nexus
  PA_HOST         www.pythonanywhere.com ou eu.pythonanywhere.com            padrão: www.pythonanywhere.com
  COMMIT_ANTERIOR commit antes do push (o pipeline preenche sozinho)
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from fnmatch import fnmatch

# nada disto vai para o servidor: banco de produção, segredos, testes, caches e arquivos do pipeline
NAO_ENVIAR = [
    "db.sqlite3", ".env", ".gitignore", "*.pyc", "*/__pycache__/*", ".github/*",
    "e2e/*", "scripts/*", "requirements-dev.txt", "run.bat",
]
COMMIT_VAZIO = "0" * 40


def avisar(texto):
    print(f"::warning::{texto}")


def falhar(texto):
    print(f"::error::{texto}")
    sys.exit(1)


def git(*args):
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def deve_enviar(caminho):
    return not any(fnmatch(caminho, padrao) for padrao in NAO_ENVIAR)


def mudancas(commit_anterior):
    """Lista (acao, caminho): 'enviar' para novos e alterados, 'apagar' para removidos."""
    if commit_anterior and commit_anterior != COMMIT_VAZIO:
        try:
            git("cat-file", "-e", f"{commit_anterior}^{{commit}}")
            linhas = git("diff", "--name-status", "--no-renames", commit_anterior, "HEAD").splitlines()
            lista = []
            for linha in linhas:
                status, caminho = linha.split("\t", 1)
                lista.append(("apagar" if status.startswith("D") else "enviar", caminho))
            return lista
        except subprocess.CalledProcessError:
            avisar("Commit anterior não encontrado; enviando todos os arquivos.")
    return [("enviar", caminho) for caminho in git("ls-files").splitlines()]


class PythonAnywhere:
    def __init__(self, host, usuario, token):
        self.base = os.environ.get("PA_API_URL") or f"https://{host}/api/v0/user/{usuario}/"
        self.token = token

    def chamar(self, metodo, caminho, corpo=None, tipo=None):
        pedido = urllib.request.Request(self.base + caminho, data=corpo, method=metodo)
        pedido.add_header("Authorization", f"Token {self.token}")
        if tipo:
            pedido.add_header("Content-Type", tipo)
        try:
            with urllib.request.urlopen(pedido, timeout=60) as resposta:
                return resposta.status, resposta.read()
        except urllib.error.HTTPError as erro:
            return erro.code, erro.read()
        except urllib.error.URLError as erro:
            falhar(f"Não consegui falar com a API do PythonAnywhere ({erro.reason}).")

    def enviar_arquivo(self, local, remoto):
        with open(local, "rb") as arquivo:
            conteudo = arquivo.read()
        fronteira = uuid.uuid4().hex
        corpo = (
            f"--{fronteira}\r\n"
            f'Content-Disposition: form-data; name="content"; filename="{os.path.basename(local)}"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n"
        ).encode() + conteudo + f"\r\n--{fronteira}--\r\n".encode()
        status, resposta = self.chamar("POST", "files/path" + urllib.parse.quote(remoto), corpo,
                                       f"multipart/form-data; boundary={fronteira}")
        if status not in (200, 201):
            falhar(f"Não consegui enviar {local} (HTTP {status}): {resposta[:200]!r}")

    def apagar_arquivo(self, remoto):
        status, resposta = self.chamar("DELETE", "files/path" + urllib.parse.quote(remoto))
        if status not in (200, 204, 404):
            falhar(f"Não consegui apagar {remoto} (HTTP {status}): {resposta[:200]!r}")

    def recarregar(self, dominio):
        status, resposta = self.chamar("POST", f"webapps/{dominio}/reload/")
        if status != 200:
            falhar(f"O reload do site falhou (HTTP {status}): {resposta[:200]!r}")


def conferir_site(dominio):
    """Abre o site algumas vezes até responder (o reload leva alguns segundos)."""
    for tentativa in range(1, 7):
        try:
            with urllib.request.urlopen(f"https://{dominio}/simulador/", timeout=30) as resposta:
                if resposta.status == 200:
                    print(f"Site no ar: https://{dominio}/ (tentativa {tentativa})")
                    return
        except Exception as erro:  # noqa: BLE001 - qualquer falha vira nova tentativa
            print(f"Tentativa {tentativa}: o site ainda não respondeu ({erro}).")
        time.sleep(10)
    falhar(f"O site https://{dominio}/ não respondeu depois do deploy.")


def main():
    token = os.environ.get("PA_API_TOKEN", "").strip()
    if not token:
        avisar("Deploy pulado: o secret PA_API_TOKEN não está configurado no GitHub (veja o README).")
        return
    dominio = os.environ.get("PA_DOMAIN", "").strip()
    usuario = os.environ.get("PA_USERNAME", "").strip() or dominio.split(".")[0]
    if not usuario:
        falhar("Configure o secret PA_USERNAME ou PA_DOMAIN.")
    dominio = dominio or f"{usuario}.pythonanywhere.com"
    pasta = (os.environ.get("PA_PROJECT_DIR", "").strip() or f"/home/{usuario}/projeto-nexus").rstrip("/")
    host = os.environ.get("PA_HOST", "").strip() or "www.pythonanywhere.com"
    api = PythonAnywhere(host, usuario, token)

    lista = [(acao, caminho) for acao, caminho in mudancas(os.environ.get("COMMIT_ANTERIOR", "").strip())
             if deve_enviar(caminho)]
    print(f"Deploy em {dominio}, pasta {pasta}: {len(lista)} arquivo(s) para atualizar.")

    for acao, caminho in lista:
        destinos = [f"{pasta}/{caminho}"]
        if caminho.startswith("static/"):
            # o PythonAnywhere pode servir os estáticos da pasta do collectstatic
            destinos.append(f"{pasta}/staticfiles/{caminho[len('static/'):]}")
        for destino in destinos:
            if acao == "apagar":
                api.apagar_arquivo(destino)
            else:
                api.enviar_arquivo(caminho, destino)
            print(f"  {acao}: {destino}")

    alterados = [caminho for _, caminho in lista]
    if any(caminho.startswith("requirements") for caminho in alterados):
        avisar("O requirements.txt mudou: rode 'pip install -r requirements.txt' no console do PythonAnywhere.")
    if any("/migrations/" in caminho for caminho in alterados):
        avisar("Há migração nova: rode 'python manage.py migrate' no console do PythonAnywhere.")

    api.recarregar(dominio)
    print("Site recarregado.")
    if not os.environ.get("PA_API_URL"):
        conferir_site(dominio)
    print(json.dumps({"dominio": dominio, "arquivos": len(lista)}))


if __name__ == "__main__":
    main()
