# Process Log — Como usei IA

> **Rascunho para minha revisão.** As decisões citadas vêm das minhas mensagens nas sessões ([integra](../evidencias/codex/mensagens-do-candidato.md), [linha do tempo](../evidencias/README.md)). Antes do PR, falta completar o trecho marcado **[COMPLETAR]**.

## Ferramentas e por quê

| Ferramenta | Quando | Uso |
|---|---|---|
| ChatGPT / Codex (agente) | 08–10/10 | Auditoria dos ZIPs, primeiro classificador, contraprova independente, dois protótipos, dez versões de apresentação |
| Claude Code (agente) | 11–12/10 | Revisão crítica da entrega anterior e reconstrução enxuta desta pasta |
| Codex CLI, `gpt-6-sol` | 11/10 | LLM de triagem durante o desenvolvimento, pela minha assinatura ChatGPT |
| Claude Haiku 5.5 (API) | publicação | LLM de triagem no site público, com tetos de uso e de gasto |
| Python: pandas, scipy, scikit-learn, Streamlit | 11–12/10 | Testes estatísticos, classificador, protótipo, testes automatizados |
| AWS (EC2, SSM, CloudFormation), Docker, Caddy | 12/10 | Deploy preparado com boas práticas |

Usei dois agentes de propósito: um construiu e o outro revisou como avaliador cético. Entre as rodadas, as decisões eram minhas.

## Como trabalhei

**Fase 1, exploração com Codex (08–10/10).** Antes de qualquer análise, questionei o volume ("se ele está mencionando 30k tickets por ano, temos que verificar", 08/10 12:42) e pedi o estudo dos datasets no Kaggle. Isso revelou 8.469 registros sintéticos, datas invertidas e marcadores sem preencher. Pedi uma **sessão independente como contraprova** (13:22), para comparar a solução feita sozinha pela IA com a que eu conduzia. Rejeitei a apresentação várias vezes, do "não entendi nada" (13:41) ao "UI genérica, claramente gerada por IA" (23:50). Também trouxe o foco de volta ao enunciado ("qual é o case? o que nos pediram?", 17:43) e exigi tratar os tickets já abertos, não só prevenir os futuros (18:27).

O resultado dessa fase foi uma auditoria de dados correta, mas 77 documentos e 87 mil palavras, nenhuma pergunta do diretor respondida com número, protótipo sem IA ao vivo e datasets nunca cruzados.

**Fase 2, revisão e reconstrução com Claude Code (11–12/10).** Pedi uma avaliação franca do que impediria a aprovação, e **prova antes de aceitar a crítica**. Em minutos saíram o teste do CSAT (nenhuma variável com p < 0,15) e um classificador simples a 86,7%. Decidi:
- a base: o núcleo da contraprova, com um app novo;
- o escopo: de 4 a 6 horas;
- o LLM: pela assinatura nos testes e API só na publicação;
- o modelo `gpt-6-sol`, quando o padrão do Codex foi recusado pela conta;
- a direção visual da apresentação, aprovada por amostra antes do resto;
- deploy real na AWS com segredos fora do código;
- recuperar informação faltante antes de perguntar ao cliente.

## Onde a IA errou e como corrigimos

| Erro | Como apareceu | Correção |
|---|---|---|
| Ressalva no lugar de resposta | Fase 1 inteira: "não é possível medir" | Ausência de sinal virou achado testado ("nada explica o CSAT") e recomendação (instrumentar) |
| Classificador fraco | 79,0% com Naive Bayes feito à mão | TF-IDF + SVM calibrado: 86,5% no teste, 85,4% sem quase-duplicatas |
| Cruzamento evitado | "Sem chave comum, não cruzar" | Transferência entre domínios; os dois achados definiram a arquitetura |
| Protótipo sem IA | 6 casos pré-processados | LLM ao vivo para qualquer texto, avaliado em amostra aleatória |
| Política conservadora demais | 77% dos casos para revisão sênior | Sênior só com risco, decisão comercial ou confiança baixa |
| Afirmação sem checar (Claude) | Disse que 139 clientes tinham vários tickets | Ao checar, cada e-mail repetido tinha um nome diferente: coincidência do gerador. O histórico do cliente saiu dos sinais reais |
| Estimativa de custo errada (Claude) | Falou em ~US$ 10/mês de AWS | Conta refeita com IPv4 público: ~US$ 17,50 na `t4g.small` ou ~US$ 11,30 na `t4g.micro` |
| Integração fora do padrão (Claude) | Chamada à Anthropic com HTTP cru e uso forçado de ferramenta | SDK oficial com structured outputs, conferido contra a documentação |
| Bugs de interface (Claude) | Clique em "Aprovar" perdia o resultado; quebra de linha dentro de string | Estado guardado em sessão; teste automatizado cobre o fluxo |
| Corte errado nas evidências (Claude) | Exportação misturou UTC e horário de Brasília e cortou mensagens decisivas | Horário de corte corrigido e conferido no arquivo final |

## O que eu adicionei

- Desconfiar do volume e dos timestamps antes de aceitar qualquer ranking.
- Criar uma contraprova independente para comparar o trabalho da IA sozinha com o trabalho conduzido.
- Exigir resposta como empresa real, com fila atual e prevenção.
- Não aceitar a primeira entrega como pronta: pedir revisão externa e prova antes de reconstruir.
- Cortar escopo (de 77 documentos para um README, um app, uma apresentação e este log).
- Definir limites de custo e de publicação, e escolher modelos.
- **[PENDENTE]** Revisar pessoalmente 20 triagens do LLM na página "Revisão humana" do app (resultado em `outputs/revisao_humana.csv`).
- **[COMPLETAR]** Contexto próprio de operação ou suporte que influenciou o desenho.

## Iterações e evidências

- Fase 1: mensagens com data e hora em [evidencias/codex](../evidencias/codex/mensagens-do-candidato.md).
- Fase 2: commits desta pasta e transcrição exportada da sessão do Claude Code.
- Resultados reproduzíveis em [outputs/](../outputs/) e teste em [tests/test_app.py](../tests/test_app.py).
