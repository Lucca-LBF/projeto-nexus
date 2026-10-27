#  Histórias de Usuário | Projeto NEXUS

Este documento contém as especificações ágeis, os critérios de aceite e os cenários de validação (BDD) das funcionalidades da plataforma web.

---

##  Simulação e Visualização de Dados
![foto das historias do usuario 1](Historias1.png)

### História de Usuário 1: Coleta de Dados do Cenário Operacional
> **Como** um Gestor de Operações,
> **Eu quero** preencher um formulário com as características específicas da minha empresa,
> **Para que** a simulação reflita a realidade financeira do meu negócio, e não um cenário genérico.

**Critérios de Aceite:**
* O formulário, com uma pergunta por tela, pergunta o tipo de empresa, o número de máquinas (ou pontos de medição), o regime de funcionamento, o custo da hora parada (ou a perda mensal, conforme o tipo de empresa), o conserto de emergência (opcional), o período de análise, a prioridade, se a empresa já tem sensores e a conexão do local.
* O formulário **não pergunta o custo do sensor**: o investimento é estimado pelo tipo de empresa, em faixa.
* O período de análise é um campo de seleção (dropdown) com 30, 60, 90, 120, 180 ou 360 dias.
* O sistema não aceita valores negativos nem zero nos campos obrigatórios, e mostra mensagens de erro em português.
* Ao concluir, o botão "Ver quanto posso economizar" envia os dados para o motor de cálculo do simulador.

**Cenários (BDD):**
```gherkin
Funcionalidade: Coleta de dados do cenário operacional

  Cenário: Preencher o formulário e ver o resultado
    Dado que estou na página do simulador
    Quando escolho o tipo de empresa e informo 100 máquinas, custo da hora parada de R$ 2.000 e período de 90 dias
    E respondo as demais perguntas
    Então o simulador calcula a simulação e abre a tela de resultado

  Cenário: Valor inválido não avança
    Dado que estou na pergunta "Número de máquinas"
    Quando informo 0 e clico em "Continuar"
    Então vejo a mensagem "Informe pelo menos 1."
    E continuo na mesma pergunta

  Cenário: O custo do sensor não é perguntado
    Dado que respondo o formulário até o fim
    Então em nenhuma tela sou perguntado sobre o preço do sensor
```

---

### História de Usuário 2: Cálculo de ROI e Viabilidade de IoT
> **Como** um Diretor Industrial,
> **Eu quero** visualizar o cálculo automático do retorno sobre o investimento e do impacto financeiro estimado com base nos dados que inseri,
> **Para que** eu possa decidir com segurança se o monitoramento com sensores IoT vale a pena para a minha empresa.

**Critérios de Aceite:**
* O sistema calcula a "Economia Bruta" comparando o custo de paradas e perdas sem IoT e com IoT, usando a redução de referência do tipo de empresa.
* O investimento é uma **estimativa de mercado em faixa** ("entre R$ X e R$ Y"), calculada pelos pontos a monitorar, pelo custo por ponto do tipo de empresa e pelos meses do período. A tela avisa que não é preço da Bzu.
* O lucro líquido estimado e o **ROI estimado** aparecem sempre na tela de resultado e usam o valor central da faixa.
* Quando o lucro seria negativo, a tela não usa vermelho nem mostra valor negativo como destaque: mostra a economia estimada, o ROI em faixa e o que falta para os sensores se pagarem.
* Se a empresa já tem sensores, o sistema mostra quanto já é evitado e quanto ainda dá para ganhar ampliando, e o investimento vale só para os pontos que ainda não têm sensor.

**Cenários (BDD):**
```gherkin
Funcionalidade: Cálculo de ROI e viabilidade de IoT

  Cenário: Resultado positivo
    Dado que informei 60 máquinas, custo da hora parada de R$ 2.000 e período de 90 dias
    Quando vejo a tela de resultado
    Então vejo o "LUCRO LÍQUIDO ESTIMADO" e o "ROI estimado" em destaque
    E vejo o investimento estimado como uma faixa, marcada como estimativa de mercado

  Cenário: Resultado que ainda não paga os sensores
    Dado que informei 60 máquinas, custo da hora parada de R$ 500 e período de 90 dias
    Quando vejo a tela de resultado
    Então vejo a "ECONOMIA ESTIMADA" em vez de um prejuízo
    E vejo o ROI estimado em faixa, sem vermelho
    E vejo quanto a redução de perdas precisa ser para os sensores se pagarem

  Cenário: Empresa que já tem sensores
    Dado que respondi que já temos sensores em alguns pontos
    Quando vejo a tela de resultado
    Então vejo quanto já é evitado com os sensores atuais
    E vejo quanto ainda dá para ganhar ampliando o monitoramento
```

---

### História de Usuário 3: Dashboard Visual de Projeção de Falhas
> **Como** um Gestor de Operações,
> **Eu quero** visualizar os dados da simulação projetados em um Dashboard interativo com gráficos,
> **Para que** eu possa comparar visualmente a eficiência da empresa com e sem a tecnologia, sem precisar analisar planilhas.

**Critérios de Aceite:**
* O Dashboard renderiza um gráfico de linhas com a projeção dos custos de falha, diária (até 30 dias) ou mensal (períodos maiores).
* O gráfico tem duas linhas distintas para comparação: "Operação Sem IoT" (Corretiva) e "Operação Com IoT" (Preditiva).
* O eixo X se adapta automaticamente ao período escolhido no formulário.
* O Dashboard mostra indicadores (resultado ou potencial de economia, investimento estimado, economia por mês e redução efetiva de perdas), o gráfico de sensibilidade com o ponto de equilíbrio e o comparativo do período.
* O Dashboard inclui uma nota explicando que o gráfico reflete a eficiência operacional, enquanto os indicadores no topo refletem o resultado financeiro.

**Cenários (BDD):**
```gherkin
Funcionalidade: Dashboard visual de projeção de falhas

  Cenário: Ver o dashboard depois de simular
    Dado que fiz uma simulação de 90 dias
    Quando abro o Dashboard
    Então vejo o gráfico de linhas "Sem IoT" e "Com IoT" com o eixo em meses
    E vejo os indicadores da simulação

  Cenário: Abrir o dashboard sem simulação
    Dado que ainda não fiz nenhuma simulação
    Quando abro o Dashboard
    Então sou levado ao formulário do simulador
```

---

##  Conversão, Atendimento e Melhoria Contínua
![foto das historias do usuario 2](Historias2.png)

### História de Usuário 4: Apresentação da Proposta de Valor e Navegação
> **Como** um Gestor de Indústria visitante,
> **Eu quero** visualizar uma página inicial clara e objetiva que explique os problemas da manutenção reativa e os benefícios da IoT,
> **Para que** eu compreenda o valor da plataforma e sinta confiança antes de investir meu tempo testando o simulador.

**Critérios de Aceite:**
* A página inicial (Home) contém o texto principal focado na dor do cliente.
* A Home tem botões de chamada para ação claros, que levam direto ao "Simulador" ou ao "Contato".
* A barra de navegação superior (Início, Simulador e Contato) aparece em todas as páginas, para o usuário navegar a qualquer momento.

**Cenários (BDD):**
```gherkin
Funcionalidade: Apresentação da proposta de valor e navegação

  Cenário: Ir da página inicial ao simulador
    Dado que estou na página inicial
    Quando clico em "Descobrir minha economia"
    Então abro o formulário do simulador

  Cenário: Ir da página inicial ao contato
    Dado que estou na página inicial
    Quando clico em "Tirar uma dúvida"
    Então abro a página de contato
```

---

### História de Usuário 5: Captação de Dúvidas e Leads Comerciais
> **Como** um Diretor Industrial interessado,
> **Eu quero** enviar uma mensagem com minhas dúvidas sobre o simulador ou um pedido de proposta comercial através de uma aba de Contato,
> **Para que** a equipe possa me retornar com um atendimento personalizado ou uma proposta técnica estruturada.

**Critérios de Aceite:**
* O formulário tem campos obrigatórios para Nome, E-mail, Assunto e Mensagem.
* O campo "Assunto" é um menu suspenso com categorias pré-definidas (Dúvida sobre o Simulador, Proposta Comercial, Feedback / Sugestões e Outros).
* Depois do envio, a página mostra um alerta visual de sucesso ("Mensagem Enviada!").
* Os dados enviados são salvos no banco de dados e ficam disponíveis no painel administrativo.

**Cenários (BDD):**
```gherkin
Funcionalidade: Captação de dúvidas e leads comerciais

  Cenário: Enviar uma mensagem de contato
    Dado que estou na página de contato
    Quando preencho nome, e-mail, assunto "Proposta Comercial" e mensagem e clico em enviar
    Então vejo o alerta "Mensagem Enviada!"
    E a mensagem fica salva no painel administrativo

  Cenário: Campo obrigatório vazio
    Dado que estou na página de contato
    Quando tento enviar sem preencher o e-mail
    Então o navegador pede o preenchimento do campo e a mensagem não é enviada
```

---

### História de Usuário 6: Compartilhamento de Feedback sobre a Experiência do Simulador
> **Como** um Gestor de Operações (cliente e usuário da plataforma),
> **Eu quero** ter um canal direto e simples para enviar críticas construtivas, relatar a minha experiência ou sugerir novas funcionalidades após usar o simulador,
> **Para que** eu possa contribuir com a evolução da ferramenta e garantir que cenários específicos da minha indústria sejam considerados em atualizações futuras.

**Critérios de Aceite:**
* O formulário de contato tem a opção "Feedback / Sugestões" no campo "Assunto", separada das opções de dúvida e de proposta comercial.
* O formulário tem um campo de texto livre e espaçoso para detalhar a crítica ou a ideia.
* O envio é rápido e aberto, sem exigir conta ou login.
* Depois de enviar, a plataforma mostra uma mensagem visual de confirmação.

**Cenários (BDD):**
```gherkin
Funcionalidade: Compartilhamento de feedback sobre a experiência do simulador

  Cenário: Enviar uma sugestão
    Dado que estou na página de contato
    Quando escolho o assunto "Feedback / Sugestões", escrevo minha ideia e clico em enviar
    Então vejo a confirmação "Mensagem Enviada!"
    E não precisei criar conta nem fazer login
```

---

### História de Usuário 7: Relatório do Resultado em PDF para Compartilhar
> **Como** um Gestor de Operações que precisa convencer a diretoria,
> **Eu quero** baixar o resultado da minha simulação em um relatório em PDF,
> **Para que** eu possa compartilhar os números com meus superiores e decidir com a equipe, sem depender de prints de tela e sem precisar refazer a simulação.

**Critérios de Aceite:**
* A tela de resultados tem um botão "Baixar relatório completo (PDF)", visível sem login ou cadastro.
* Ao clicar, o navegador abre a janela de impressão, de onde o usuário salva o arquivo com "Salvar como PDF".
* O relatório contém o cabeçalho com a marca BZU, o segmento e a data de geração, o resumo dos dados informados, o resultado e o ROI estimados, o investimento estimado em faixa, o gráfico de projeção de custos, o "Como calculamos" já aberto e a interpretação do resultado.
* O relatório não exibe menu, rodapé do site nem botões, e cabe em páginas A4 legíveis.
* O rodapé do relatório traz o contato da Bzu (e-mail e site) e o aviso de que os valores são estimativas feitas com premissas de referência.

**Cenários (BDD):**
```gherkin
Funcionalidade: Relatório do resultado em PDF

  Cenário: Baixar o relatório
    Dado que estou na tela de resultado de uma simulação
    Quando clico em "Baixar relatório completo (PDF)"
    Então o navegador abre a janela de impressão
    E posso escolher "Salvar como PDF"

  Cenário: Conteúdo do relatório
    Dado que abri o relatório
    Então vejo a marca BZU, o segmento, a data, os dados informados, o resultado e o ROI estimados e o gráfico
    E não vejo menu nem botões
```
