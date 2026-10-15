# Evidências do processo

| Arquivo | O que é |
|---|---|
| [codex/mensagens-do-candidato.md](codex/mensagens-do-candidato.md) | As 105 mensagens que digitei nas sessões do Codex (08 a 10/10), em ordem e sem edição, exportadas dos registros locais por [`analysis/export_codex_log.py`](../analysis/export_codex_log.py) |
| Histórico Git desta pasta | A reconstrução com Claude Code (11 e 12/10), um commit por etapa |
| [../outputs/revisao_resumo.json](../outputs/revisao_resumo.json) | Revisão de 20 triagens do LLM por dois revisores de IA (Claude e Codex, este sem ver a revisão do Claude). Não houve revisão humana |

As versões feitas com o Codex não estavam em Git, então não há commits antigos. Não criei commits com datas retroativas: a linha do tempo abaixo usa os horários reais das sessões.

## Linha do tempo das decisões (horário de Brasília)

| Quando | O que eu disse (resumo; texto integral no arquivo) | O que mudou |
|---|---|---|
| 08/10 12:10 | O centro é trabalhar e apresentar como um AI Master, no modelo que a diretoria do G4 espera | Critério de sucesso passou a ser a apresentação para a diretoria, não só o resultado técnico |
| 08/10 12:42 | "se ele está mencionando 30k tickets por ano, temos que verificar"; pedi para ser entrevistado com opções antes de decidir | Auditoria dos dados antes de qualquer análise; padrão de entrevista antes de executar |
| 08/10 12:45 | Pedi para estudar os datasets no Kaggle e os casos de uso dos autores | Descoberta de que o volume real é 8.469 e de que os dados são sintéticos |
| 08/10 13:22 | Pedi uma sessão independente como contraprova, sem as minhas decisões, para comparar | Nasceu a `contraprova-autonoma`, base analítica da versão final |
| 08/10 13:41 | "a apresentação está fraca... só tem fazer triagem de um ticket em inglês que não resolve o problema" | Primeira de várias rejeições da apresentação |
| 08/10 17:43 | "voltando ao problema que nos foi proposto, qual é o case? o que nos pediram?" | Volta ao enunciado depois de horas em direção visual |
| 08/10 17:59 | Os datasets são ruins, mas assumir que isso é intencional e responder como se fosse a empresa | Tratar defeitos de dados como achados, não como desculpa |
| 08/10 18:27 | Além de prevenir tickets futuros, corrigir os que já estão abertos, incoerentes ou mal respondidos | Plano em duas frentes, recuperar a fila e prevenir; hoje a cena "Na segunda-feira" |
| 08/10 19:02 | "faz sentido a gente corrigir anotações? não estaríamos influenciando a base?" | Preservar os originais e separar o que é simulado |
| 08/10 19:59 | A apresentação parece produto para usuário final, não para diretoria | Virada para o formato executivo |
| 08/10 23:50 | "site muito denso, UI genérica, claramente gerada por IA" | Mais rodadas visuais no Codex, sem chegar lá |
| 09/10 14:14 | "o gancho está fraco e está esperando interação para mostrar dados" | O problema só foi resolvido na versão final, com a abertura automática |
| 11/10 | Pedi ao Claude Code uma avaliação franca de por que a entrega não seria aprovada, e prova antes de aceitar a crítica | Reconstrução enxuta: testes estatísticos, classificador melhor, LLM ao vivo, cruzamento dos datasets |
| 11/10 | Escolhi a base (núcleo da contraprova), o escopo de 4 a 6 h, o LLM pela assinatura nos testes e o modelo `gpt-6-sol` | Ver histórico Git |
| 12/10 | Pedi gancho mais forte, deploy real na AWS com boas práticas e recuperação de informações faltantes | Abertura com o ticket 609, deploy pronto e painel de contexto |
| 12/10 | Pedi site mais impressionante, com 3D, pensado para o avaliador; escolhi a abertura A entre três | Apresentação 3D com Three.js e capítulo "Como trabalhei com a IA" |
| 15/10 | Sem tempo para validar, pedi que o Claude fizesse os testes e usasse o Codex como segunda opinião | Revisão das 20 triagens por dois revisores de IA, registrada como revisão por IA |
