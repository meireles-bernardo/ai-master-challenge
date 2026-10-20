# Submissão — Bernardo Meireles Correa — Challenge 002

## Sobre mim

- **Nome:** Bernardo Meireles Correa
- **LinkedIn:** https://www.linkedin.com/in/bernardomeirelescorrea/
- **Challenge escolhido:** 002 — Redesign de Suporte

---

## Para avaliar em 2 minutos

| O quê | Onde | O que olhar |
|---|---|---|
| **Dossiê** (3 min de leitura) | **https://g4.bernardomeirelescorrea.com.br** | A capa dá o veredito sobre o suporte; as cinco provas trazem o dado, a fonte e o que fazer; o plano mostra para onde cada ticket vai |
| **Protótipo no ar** | **https://g4.bernardomeirelescorrea.com.br/app/triagem** | Sorteie um ticket e clique em *Analisar*: a IA responde em poucos segundos e o mapa ao lado acende o destino. *Painel*, *Fila* e *Método* estão no menu do topo |
| **Vídeo** (76 s) | [`presentation/video/demo-dossie-002.mp4`](presentation/video/demo-dossie-002.mp4), também em https://g4.bernardomeirelescorrea.com.br/video/demo-dossie-002.mp4 | Dossiê, uma triagem real com o mapa e a fila, narrados. [Como foi feito](evidencias/video/README.md) |
| **Rodar localmente** | `cd submissions/bernardo-meireles-correa` e os três comandos de [Como rodar](#como-rodar-2-min) | Sem chave de API tudo funciona, menos a triagem de clientes por LLM. O dossiê também abre direto do arquivo `presentation/index.html`, sem internet |

O site fica no ar durante a avaliação. Base: os datasets públicos do desafio; o de clientes é sintético.

---

## Executive Summary

Analisei os 8.469 tickets de clientes com testes estatísticos: 67% da fila está parada (2.819 tickets nunca tiveram primeira resposta), a prioridade declarada não muda nada (66% dos *Critical* estão parados, como os *Low*) e nenhuma das 8 variáveis testadas explica a nota de satisfação. Com os 47.837 tickets de TI treinei um classificador que encaminha sozinho 74% dos casos com 95% de acerto; nos tickets de clientes, um LLM faz a triagem e uma regra fixa decide o que exige uma pessoa, sem nenhuma promessa indevida nos 60 tickets testados. A estimativa é de cerca de 212 horas por mês recuperáveis, com premissas que o piloto vai medir. Recomendação: atender a fila por risco já nesta semana, sem IA, e rodar quatro semanas de IA em sombra antes de automatizar qualquer resposta.

---

## Solução

### Como rodar (≈2 min)

```bash
cd submissions/bernardo-meireles-correa            # a partir da raiz do repositório do desafio
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt      # macOS/Linux: .venv/bin/pip
.venv/Scripts/streamlit run app/app.py             # abre http://localhost:8501
```

Ou acesse a versão hospedada: **https://g4.bernardomeirelescorrea.com.br** (dossiê) e **https://g4.bernardomeirelescorrea.com.br/app/** (protótipo). O deploy na AWS (EC2, Docker Compose, Caddy com HTTPS, chave no SSM, sem SSH) está descrito em [deploy/README.md](deploy/README.md).

O modelo e os resultados já vêm no repositório. A triagem de clientes usa um LLM configurado por `LLM_PROVIDER`:

| Valor | Uso |
|---|---|
| `anthropic` | Claude Haiku 5.5 via SDK oficial (produção); defina `ANTHROPIC_API_KEY` |
| `openai` | API da OpenAI; defina `OPENAI_API_KEY` e `LLM_MODEL` |
| `codex` | Assinatura ChatGPT via Codex CLI (usado no desenvolvimento) |
| `off` | Sem LLM; classificador, regras, fila e evidências continuam funcionando |

Para reproduzir tudo a partir dos ZIPs do Kaggle (ver [data/README.md](data/README.md)): `python analysis/diagnose.py`, `python analysis/train.py`, `python analysis/eval_llm.py` e `python analysis/build_presentation.py` (atualiza os números da apresentação). O teste de fumaça do app é `python tests/test_app.py`.

### Abordagem

1. **Desconfiar dos dados antes de ranquear.** Antes de qualquer média, verifiquei se as métricas eram consistentes. Os timestamps cobrem 27 horas, 49% dos tickets fechados têm a resolução *antes* da primeira resposta, todas as descrições trazem o marcador `{product_purchased}` sem preencher e as resoluções são frases sem sentido. O Dataset 1 é sintético.
2. **Testar em vez de ranquear.** Pedir as "piores combinações" a uma IA gera um ranking. Aqui testei se as diferenças existem (Kruskal-Wallis, qui-quadrado, permutação), e elas não existem. Isso mudou a resposta de "invista no canal X" para "o problema é a fila".
3. **Usar cada dataset no que ele tem de verdadeiro.** O de TI tem texto e rótulos coerentes, então treinei e validei um classificador nele. O de clientes tem a estrutura da operação (status, prioridade, canal), mas os rótulos não têm relação com o texto. Por isso o lado de clientes usa um LLM sem treino (zero-shot), avaliado com verificações objetivas.
4. **Separar o que a IA sugere do que a regra decide.** O LLM e o classificador sugerem. Regras determinísticas, com uma rede de segurança por palavras-chave, decidem o que exige humano.

### Resultados / Findings

**Diagnóstico (Dataset 1, 8.469 tickets)**

| Pergunta | Resposta | Evidência |
|---|---|---|
| Onde o fluxo trava? | Na fila, igual em todos os segmentos | 5.700 tickets (67%) não fechados; a proporção de status é a mesma por canal, prioridade e tipo (V de Cramér ≤ 0,03) |
| Quais combinações são piores? | Nenhuma, estatisticamente | 80 combinações com 8 a 28 tickets cada; Kruskal-Wallis p = 0,46; a "pior" surge por acaso em 13% das permutações |
| A prioridade funciona? | Não | 1.403 dos 2.129 *Critical* (66%) estão parados, como os *Low* |
| O que impacta a satisfação? | Nenhuma relação detectável nas 8 variáveis testadas | CSAT 2,99; notas 553/549/580/543/544; canal p = 0,47, prioridade p = 0,40, tipo p = 0,26, tempo ρ = 0,02 |
| Quanto se desperdiça? | 112 a 279 h/mês recuperáveis, 212 no cenário central | Premissas explícitas e editáveis no app (Como validamos → Retorno estimado); o dataset não registra o esforço do agente |

**Automação (os dois datasets)**

| Componente | Resultado |
|---|---|
| Classificador de TI (TF-IDF + SVM calibrado) | 86,5% de acurácia em 9.568 tickets não vistos; 85,4% sem quase-duplicatas; linha de base 28,5% |
| Limiar de confiança | 74% roteados sozinhos com 95,0% de precisão; 26% vão para triagem humana |
| Por que não 99% | 3,9% dos textos quase idênticos têm rótulos diferentes no próprio dataset, então o teto fica perto de 96%. O que se ajusta é o limiar: 99% de meta dá 98,8% de acerto medido, mas só 49% vão sozinhos ([`analysis/classifier_curve.py`](analysis/classifier_curve.py)) |
| Cruzamento 1 | Aplicado aos tickets de clientes, o classificador de TI passaria 61% com confiança alta, em categorias absurdas. A confiança não detecta texto de outro domínio, então o roteador é escolhido pela origem do ticket |
| Cruzamento 2 | O texto de clientes prevê tipo, assunto e prioridade no nível do acaso (19,8% contra 20,7% no tipo). Não dá para treinar com esses rótulos, o que justifica o LLM zero-shot |
| Triagem por LLM (60 tickets sorteados) | Rodada com o modelo de produção (Claude Haiku 5.5, pela API): 60/60 processados; 0 promessas proibidas; 0 dos 11 riscos apontados pela regra ficaram sem marcação do LLM; 5 de 5 mensagens de erro em branco pedidas ao cliente; 30 casos assistidos e 30 com revisão sênior; US$ 0,0004 por ticket. Clareza do ticket: 13 alta, 38 média, 9 baixa (o texto sintético costuma permitir mais de uma leitura). A rodada anterior, com `gpt-6-sol`, está em `outputs/llm_eval_v1_codex.json` e é a base das 20 revisões por IA |

**Protótipo (Streamlit, 4 páginas):**
- *Painel da operação*: indicadores da fila, situação por prioridade e por canal, satisfação e o topo da fila já reordenada.
- *Triagem*: aceita qualquer texto ou sorteia registros dos datasets. Mostra primeiro o destino e o próximo passo, depois o que pedir ao cliente e o rascunho para aprovar, editar ou rejeitar. Ao lado, um mapa de próximos passos acende o caminho que o ticket percorreu nas regras, com quem age e por quê.
- *Fila*: os 5.700 tickets parados reordenados por risco, com filtros.
- *Como validamos*: classificador de TI, triagem por LLM, revisão das 20 triagens por dois revisores de IA (Claude e Codex) e retorno estimado com premissas ajustáveis.

**Fluxo proposto**

```
ticket entra → origem? ─ TI ──────→ classificador ─ confiança ≥ limiar → fila da categoria (Acesso/Admin/Compra: dono aprova a execução)
                  │                                └ abaixo ──────────→ triagem humana
                  └ cliente → LLM: tipo, prioridade, riscos, dados faltantes, rascunho
                              + regra de palavras-chave (rede de segurança)
                              → risco, reembolso/cancelamento ou ticket confuso → agente sênior
                              → demais → agente revisa o rascunho e pede o que falta → envia
```

**Recuperar o que falta antes de perguntar de novo ao cliente.** 34% da fila espera o cliente mandar algo que faltou. Antes de perguntar, a IA procura:

| Fonte | Nesta base | No protótipo |
|---|---|---|
| O próprio texto | Contatos e trechos de log citados (145 tickets) | Extraídos e mostrados ao agente |
| Cadastro | Produto e data de compra; todas as compras têm mais de 12 meses (fora de uma garantia de 12 meses, que é premissa minha; a política real precisa ser confirmada) | Mostrados ao agente |
| Campos em branco | 472 tickets sem a mensagem de erro | Sinalizados; a telemetria do produto poderia supri-la |
| E-mail do suporte, CRM, histórico do cliente | Não existem no dataset | **Simulados:** o app mostra a consulta que faria, nunca um resultado inventado |

Regras exigidas antes de conectar fontes reais (LGPD): somente leitura, só conversas ligadas ao ticket ou ao cliente, mínimo necessário, cada consulta registrada e nada enviado sem uma pessoa aprovar. **Hoje elas são requisitos de desenho, não controles implementados**: as fontes do protótipo são simuladas, então não há autorização nem auditoria de consultas para testar.

**Segurança do LLM num site público.** O texto do ticket é dado não confiável, e o LLM pode ser influenciado por ele: no ticket 4716, o rascunho repetiu um pedido que veio do próprio texto (dar crédito a @joeyclay). Por isso o desenho não depende de o LLM resistir a isso. O LLM não tem ferramentas nem acesso a sistemas; a saída tem schema fixo (structured outputs); quem decide o destino é a regra determinística, que também procura riscos por palavra-chave, mesmo que o modelo seja manipulado. Recusas do modelo viram triagem humana. Custos: limite por visita, teto diário e teto de gasto no provedor.

**Scan de segurança antes de publicar** (19/10, repetido em 20/10 antes do push). A CI em `.github/workflows/ci.yml` repete esses passos quando esta pasta roda como repositório próprio; dentro do repositório do desafio, o GitHub só executa workflows da raiz, então ali ela não roda.

| Verificação | Ferramenta | Resultado |
|---|---|---|
| Segredos no histórico Git e nos arquivos | Gitleaks 8.21 | Nenhum |
| Dados pessoais e da máquina (e-mail, caminhos, IDs, IPs, telefones, CPF, tokens) | Varredura própria | Um caminho local nas mensagens exportadas, omitido; o resto são falsos positivos (hash, e-mail sintético do dataset) |
| Dependências Python | pip-audit | Nenhuma vulnerabilidade conhecida |
| Código Python | Bandit | 7 avisos, nenhum explorável (chamada ao Codex sem shell, URL fixa, sorteio não criptográfico) |
| Imagem Docker | Trivy 0.57 | 0 críticas; 44 altas em pacotes do Debian 13 sem correção publicada, em ferramentas que o app não usa e que exigem privilégios que o contêiner não tem |
| Stack em produção local (Caddy + app) | Testes HTTP | HTTPS com redirecionamento, cabeçalhos de segurança, `.env`, scripts e `.git` não servidos (404) |

### Recomendações

1. **Esta semana:** reordenar a fila por risco (perda de dados, dinheiro, acesso, cancelamento, jurídico) e primeiro contato. A regra roda sem IA e já está no protótipo.
2. **Próximas 4 semanas, piloto em sombra:** IA na triagem e no rascunho da primeira resposta, com o humano decidindo e nada sendo enviado automaticamente. Placar para decidir ao fim:

   | Métrica | Escalar se | Parar se |
   |---|---|---|
   | Minutos poupados por ticket (medidos) | ≥ 2 min | < 1 min |
   | Rascunhos enviados com no máximo pequenas edições | ≥ 70% | < 40% |
   | Casos de risco que a IA deixou passar (com gabarito humano) | 0 | qualquer um sem a regra pegar |
   | Recontato do cliente em 7 dias | igual ou menor que antes | maior que antes |
   | Custo de LLM por ticket | < US$ 0,01 | — |
3. **Instrumentar:** registrar a abertura do ticket, cada mudança de status e o motivo de cada nota baixa. Sem isso, nenhum SLA ou ganho de CSAT é demonstrável.
4. **Não automatizar:** reembolso, cancelamento, perda de dados, acesso e segurança, e casos jurídicos. Exemplos dos dados: o ticket com perda de dados após atualização vai para o sênior, mesmo com o LLM confiante.
5. **Só depois do piloto:** resposta automática para perguntas informativas, sem risco e com o ticket claro (clareza alta). Nesta base, nenhum ticket se qualificou, porque todos chegam sem algum dado necessário.

### Limitações

- O Dataset 1 é sintético. As conclusões de **processo** (fila, prioridade ignorada, falta de instrumentação) orientam o desenho, mas os tempos e o CSAT absolutos não descrevem uma operação real.
- O ROI depende de minutos assumidos, porque o dataset não registra esforço. Capacidade liberada não vira caixa automaticamente.
- A avaliação do LLM usa verificações automáticas em 60 tickets e a revisão de 20 deles por dois revisores de IA (Claude e, sem ver a revisão do Claude, o Codex). Os dois discordaram do LLM nos mesmos três pontos: o tipo de 1 ticket e a prioridade de 2. Testei a triagem no site publicado, com tickets sorteados e a API real, e revisei os resultados. Foi assim que encontrei o campo de confiança sem critério (virou "Clareza do ticket", com critério no prompt e uma nova avaliação dos 60 tickets) e questionei o limite do classificador. A revisão sistemática das 20 triagens da amostra foi feita por dois revisores de IA (Claude e Codex). Uma revisão humana sistemática é o primeiro passo do piloto.
- Custo do LLM: com os preços do Claude Haiku 5.5 (US$ 0,10 e 0,50 por milhão de tokens de entrada e saída), o custo medido na avaliação dos 60 tickets foi de US$ 0,0004 por ticket (cerca de 1.300 tokens de entrada e 535 de saída); o ROI usa US$ 0,01 por cautela.
- O classificador de TI vale para aquela organização e em inglês. Não há integração com helpdesk, autenticação nem envio real.

---

## Process Log — Como usei IA

Resumo abaixo; a narrativa completa, com as versões anteriores e as decisões, está em [process-log/README.md](process-log/README.md).

### Ferramentas usadas

| Ferramenta | Para que usou |
|---|---|
| ChatGPT / Codex | Primeiras 10 iterações: auditoria dos dados, primeiro classificador, dois protótipos e documentação |
| Claude Code | Revisão crítica da entrega e reconstrução enxuta: testes estatísticos, novo classificador, app Streamlit, avaliação do LLM |
| Codex CLI (`gpt-6-sol`) | LLM de triagem dentro do app durante o desenvolvimento, via assinatura |
| Claude Haiku 5.5 (API) | LLM de triagem no site público, com tetos de uso e de gasto |
| Python (pandas, scipy, scikit-learn, Streamlit) | Cálculos, modelo e protótipo |
| AWS, Docker, Caddy, GitHub Actions | Deploy e CI |

### Workflow

1. Auditoria dos dois ZIPs com o Codex, que achou os timestamps invertidos e os marcadores sem preencher.
2. Dez versões de protótipo e apresentação, com críticas minhas a cada rodada.
3. Revisão externa com o Claude Code. A conclusão foi que a entrega tinha virado um tratado de ressalvas, com 77 documentos e 87 mil palavras, sem responder às perguntas do diretor e sem IA generativa rodando.
4. Reconstrução enxuta: testes estatísticos, classificador com split limpo e limiar calibrado, LLM com política determinística, app, avaliação em amostra aleatória e apresentação.
5. Gancho com um ticket real, recuperação de contexto, revisão das triagens por dois revisores de IA e deploy na AWS preparado com boas práticas.

### Onde a IA errou e como corrigi

- **Paralisia por ressalvas:** a IA tratou "dados sintéticos" como motivo para não responder. Reescrevi: dado sem sinal é um achado (nenhuma relação detectável com o CSAT) e vira recomendação (instrumentar).
- **Afirmações fortes demais, apontadas pela revisão do Codex:** "nenhum risco perdido", "o texto nunca é tratado como instrução", "a fila anda por ordem de chegada". Reescrevi cada uma para dizer só o que foi medido; o teto diário de chamadas passou a ser reservado antes da chamada.
- **Classificador fraco:** a primeira versão (Naive Bayes feito à mão) teve 79,0%. Um baseline de 8 linhas deu 86,7%, e a versão final teve 86,5% no holdout limpo.
- **Recusa em cruzar os datasets:** a IA evitou o cruzamento por falta de chave. O cruzamento por transferência mostrou dois fatos que mudaram o desenho.
- **Protótipo sem IA:** havia 6 casos pré-processados e a API estava "adiada". Agora o app aceita qualquer texto e o LLM roda ao vivo.
- **Política conservadora demais:** na primeira rodada, 77% dos casos iam para revisão sênior. Ajustei para o sênior receber só risco, decisão comercial ou confiança baixa.
- **Afirmação sem checar:** a IA disse que 139 clientes tinham vários tickets. Conferindo, cada e-mail repetido tinha um nome diferente, ou seja, coincidência do gerador sintético. O histórico do cliente saiu dos sinais reais e ficou como fonte simulada.
- **Custo subestimado:** a primeira estimativa de AWS ignorava a cobrança do IPv4 público. Refeita: ~US$ 17,50/mês na `t4g.small` ou ~US$ 11,30 na `t4g.micro`.

### O que eu adicionei que a IA sozinha não faria

- Desconfiei do volume (30 mil anunciados contra 8.469 reais) antes de aceitar qualquer ranking de atraso.
- Criei uma contraprova independente para comparar o que a IA faz sozinha com o que eu conduzo.
- Exigi resposta como empresa real: recuperar a fila atual além de prevenir, e buscar o dado faltante antes de perguntar de novo ao cliente.
- Rejeitei entregas que pareciam prontas, pedi revisão externa e prova antes de reconstruir, e cortei escopo.

Detalhes, com data e hora das minhas mensagens, em [process-log/README.md](process-log/README.md) e [evidencias/](evidencias/README.md).

---

## Evidências

- [x] Linha do tempo das decisões, com data e hora: [evidencias/README.md](evidencias/README.md)
- [x] A ferramenta funcionando: [dossiê](https://g4.bernardomeirelescorrea.com.br) e [protótipo](https://g4.bernardomeirelescorrea.com.br/app/triagem) no ar
- [x] Git history: um commit por etapa da reconstrução
- [x] Resultados reproduzíveis: [diagnóstico](outputs/diagnostico.json), [classificador](outputs/classifier_metrics.json), [erros do modelo](outputs/classifier_errors.csv), [avaliação do LLM](outputs/llm_eval.json)
- [x] Narrativa escrita: [process-log/README.md](process-log/README.md)
- [x] Revisão de 20 triagens por dois revisores de IA: [Claude](outputs/revisao_claude.csv), [Codex](outputs/revisao_codex.csv), [resumo](outputs/revisao_resumo.json)

---

_Submissão enviada em: 20/10/2026_
