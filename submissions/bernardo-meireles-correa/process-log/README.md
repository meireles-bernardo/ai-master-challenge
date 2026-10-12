# Process Log — Como usei IA

> **Rascunho para revisão do candidato.** Os trechos marcados com **[CONFIRMAR]** descrevem decisões minhas registradas nas sessões. Precisam ser conferidos e completados por mim antes do PR.

## Ferramentas e por quê

| Ferramenta | Fase | Uso |
|---|---|---|
| ChatGPT / Codex (agente) | 08–09/10 | Auditoria dos ZIPs, primeiro classificador, dois protótipos (Python e Node/React), dez versões de apresentação |
| Claude Code (agente) | 11/10 | Revisão crítica da entrega anterior e reconstrução enxuta desta pasta |
| Codex CLI, modelo `gpt-6-sol` | 11/10 | LLM de triagem dentro do app, chamado pela minha assinatura ChatGPT durante os testes. Na publicação, a troca para API é só configuração |
| Python: pandas, scipy, scikit-learn, Streamlit | 11/10 | Testes estatísticos, classificador, protótipo e teste automatizado do app |

Usei dois agentes de propósito: um construiu, o outro revisou como avaliador cético. Os dois rodavam nos meus arquivos locais, e eu decidia entre as rodadas.

## Linha do tempo

### Fase 1: exploração com ChatGPT/Codex (dez iterações)

1. **Auditoria antes de análise.** Pedi que os ZIPs fossem lidos antes de qualquer conclusão. O agente achou o volume real (8.469, não ~30 mil), o marcador `{product_purchased}` em 100% das descrições e 1.365 dos 2.769 fechados com datas invertidas. **[CONFIRMAR]** Questionei o volume, as fontes e os timestamps quando o primeiro rascunho começou a ranquear atrasos.
2. **Primeiro classificador** (Naive Bayes escrito à mão, com treino, calibração e teste separados): 79,0% de acurácia.
3. **Dois protótipos concorrentes.** Uma solução em Python, com relatório e carteira de recuperação, e outra em Node/React, com dois fluxos demonstrativos e motion.
4. **Dez versões visuais.** **[CONFIRMAR]** Rejeitei várias versões da apresentação por estarem centradas no produto e não no problema do diretor.

O que saiu dessa fase: uma auditoria de dados correta e honesta, mas **77 documentos e 87 mil palavras**, nenhuma das três perguntas do diretor respondida com um número, protótipo sem IA generativa ao vivo (6 casos pré-processados, API "adiada") e nenhum cruzamento entre os datasets.

### Fase 2: revisão crítica e reconstrução com Claude Code

5. **Revisão como avaliador.** Pedi ao Claude Code uma avaliação franca do que impediria a aprovação. O diagnóstico teve sete pontos: ressalvas no lugar de respostas, protótipo sem IA, recusa em cruzar os datasets, classificador fraco, excesso de material, process log que apagava o candidato e duas soluções concorrentes.
6. **Prova rápida antes de reescrever.** Antes de aceitar a crítica, pedi evidência. Em minutos saíram o teste de associação do CSAT (nenhuma variável com p < 0,15; notas uniformes) e um baseline de 8 linhas a 86,7%, que mostrou que a crítica tinha base.
7. **Decisões de escopo (minhas):** partir do núcleo analítico da solução Python e criar um app novo; escopo enxuto de 4 a 6 horas; LLM pela assinatura nos testes e API real só na publicação; modelo `gpt-6-sol` quando o padrão do meu Codex foi recusado pela conta.
8. **Construção:** diagnóstico com testes (qui-quadrado, Kruskal-Wallis, permutação, Spearman); classificador com split limpo, limiar calibrado para 95% de precisão e teste sem quase-duplicatas; dois testes de cruzamento; camada de LLM com provedores intercambiáveis e política determinística; avaliação do LLM em 60 tickets sorteados; app Streamlit; teste automatizado de ponta a ponta.

## Onde a IA errou e como corrigimos

| Erro | Como apareceu | Correção |
|---|---|---|
| Ressalva no lugar de resposta | "Não é possível medir desperdício nem causa do CSAT" em toda a fase 1 | Ausência de sinal virou achado testado ("nada explica o CSAT", "as piores combinações são ruído") e recomendação (instrumentar) |
| Classificador fraco | 79,0% com Naive Bayes feito à mão | TF-IDF + SVM calibrado: 86,5% no holdout; 85,4% sem quase-duplicatas |
| Cruzamento evitado | "Sem chave comum, não cruzar" | Transferência: o modelo de TI passaria 61% dos tickets de clientes com confiança alta, e o texto de clientes não prevê seus rótulos. Os dois fatos definiram a arquitetura |
| Protótipo sem IA | 6 casos pré-processados | LLM ao vivo para qualquer texto; avaliação em amostra aleatória com semente fixa |
| Política conservadora demais | 1ª rodada: 77% dos casos para revisão sênior, nenhum assistido | Sênior só com risco, decisão comercial ou confiança baixa; confiança média vai para o agente comum (31 assistidos, 29 sênior) |
| Bug de interface (Claude) | No Streamlit, o clique em "Aprovar" recarregava a página e perdia o resultado | Estado guardado em `session_state`; teste automatizado cobre aprovar e registrar |
| Modelo grande demais (Claude) | 26 MB, pesado para um PR | Vocabulário de 100 mil termos e um único SVM calibrado: 5,6 MB, sem perda de acurácia |
| Modelo padrão inválido | `gpt-6.1-sol` recusado pela conta ChatGPT | O agente parou e perguntou; eu escolhi `gpt-6-sol` |

## O que eu adicionei

- **[CONFIRMAR]** Desconfiar do volume e dos timestamps antes de aceitar qualquer ranking de atraso.
- **[CONFIRMAR]** Exigir que cada lacuna dos dados fosse explicada em termos que um diretor entendesse.
- Não aceitar a primeira entrega como pronta e buscar uma segunda opinião de outro agente, como avaliador.
- Pedir prova antes de aceitar a crítica, e só então decidir reconstruir.
- Cortar escopo: de 77 documentos e duas soluções para um README, um app e este log.
- Decidir os limites de custo (assinatura nos testes, API só na publicação) e escolher o modelo.
- **[COMPLETAR]** Contexto próprio de operação ou suporte que influenciou o desenho, por exemplo por que a fila por risco vem antes da automação.

## Iterações e evidências

- Fase 1: dez versões documentadas (preservadas fora desta pasta, no histórico local).
- Fase 2: commits desta pasta; resultados em [outputs/](../outputs/); teste em [tests/test_app.py](../tests/test_app.py).
- **[COMPLETAR]** Screenshots ou export das conversas mais decisivas: a revisão crítica e as escolhas de escopo.
