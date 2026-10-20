# Vídeo de demonstração (76 s)

Arquivo: [`presentation/video/demo-dossie-002.mp4`](../../presentation/video/demo-dossie-002.mp4), também servido em https://g4.bernardomeirelescorrea.com.br/video/demo-dossie-002.mp4.

Mostra o dossiê e o protótipo no ar: capa, provas, a Prova 05 com a curva do classificador, uma triagem real (ticket sorteado, chamada à API do Claude Haiku 5.5 e o mapa acendendo o caminho), a fila em ordem de risco e o endereço.

## Como foi feito

| Etapa | Ferramenta | Observação |
|---|---|---|
| Captura | Playwright com o screencast do DevTools, 1920×1080, a partir do site publicado em 20/10/2026 | Seis trechos, um por bloco da narração; o cursor vermelho é desenhado na página para mostrar os cliques |
| Narração | Higgsfield, voz Dylan (ElevenLabs v3), português | Uma geração de 74,2 s, sem edição de pitch ou velocidade |
| Montagem | FFmpeg | A narração define o tempo; cada trecho foi cortado ou acelerado (até 1,5×) para durar o bloco correspondente; legendas frase a frase |
| Finalização | Limpeza de metadados com recibo | Áudio a -16,5 LUFS, pico -1,0 dBFS; decodificação completa sem erro |

O roteiro foi escrito com o Claude Code a partir dos números do dossiê; autorizei a narração depois de lê-lo.

## Roteiro

1. Este é o Dossiê 002: uma análise independente de 8.469 tickets de suporte. Dois terços estão parados, e a prioridade declarada não muda isso.
2. Cada prova traz o dado, a fonte e o que fazer. Os tickets críticos estão parados na mesma proporção dos de prioridade baixa. E nenhuma das oito variáveis testadas explica a nota do cliente.
3. A IA foi testada antes de entrar na proposta. Nos tickets de TI, o classificador encaminha sozinho três em cada quatro, com 95% de acerto. O restante vai para uma pessoa.
4. No protótipo, a triagem roda ao vivo. Sorteio um ticket do dataset e peço a análise. Em poucos segundos aparecem o destino, o que pedir ao cliente e um rascunho de resposta.
5. O mapa mostra o caminho que esse ticket fez. Quem decide o destino é uma regra fixa: reembolso, cancelamento, perda de dados e acesso sempre passam por uma pessoa.
6. Na fila, os tickets parados aparecem em ordem de risco. Dá para começar por ela nesta semana, sem IA.
7. O dossiê e o protótipo estão no ar, no endereço que aparece na tela.

## Integridade

| Arquivo | SHA-256 |
|---|---|
| `demo-dossie-002.mp4` (final) | `c761dbf7defbc5b3991c773ce85db003b60dea4b3920d00a5ef9210892cb1c82` |
| Narração original (MP3 do Higgsfield) | `e573014c1161181175c7a4ed75a3a94cb7963d2ea32b55589a0ec68b00e1b7e1` |
