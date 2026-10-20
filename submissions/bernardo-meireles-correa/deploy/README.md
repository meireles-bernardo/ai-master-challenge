# Deploy na AWS

Uma EC2 ARM roda Docker Compose com dois contêineres. Custo mensal aproximado em us-east-1 (on-demand):

| Item | `t4g.small` (2 GB) | `t4g.micro` (1 GB) |
|---|---:|---:|
| Instância | ~US$ 12,30 | ~US$ 6,10 |
| Disco gp3 20 GB | ~US$ 1,60 | ~US$ 1,60 |
| IPv4 público (cobrado à parte) | ~US$ 3,60 | ~US$ 3,60 |
| **Total** | **~US$ 17,50** | **~US$ 11,30** |

Desligar a instância fora do período de avaliação zera o custo da instância; disco e IP continuam sendo cobrados.

```
Internet ─HTTPS─▶ Caddy  ── /      → apresentação estática
                         └─ /app/* → app Streamlit (contêiner sem root, filesystem somente leitura)
Chave da Anthropic ─▶ SSM Parameter Store (SecureString) ─▶ lida no boot pelo papel IAM da instância
```

Sem SSH: o acesso ao servidor é pelo SSM Session Manager. IMDSv2 obrigatório, disco criptografado e security group só com 80/443. O papel IAM pode ler apenas o parâmetro da chave (`ssm:GetParameter`) e usar `kms:Decrypt` somente em chamadas feitas pelo SSM na região (condição `kms:ViaService`), o que cobre a chave padrão `aws/ssm`; para restringir a uma chave KMS específica, crie o parâmetro com uma chave própria e troque o `Resource`.

## Quem faz o quê

| Passo | Quem |
|---|---|
| Login na AWS (`aws login`), criar a chave na Anthropic, gravar no SSM, teto de gasto | Dono da conta |
| Criar o registro A no Cloudflare | Dono do domínio |
| Template, scripts, compose, verificação | Já estão neste repositório |

## Atalho

Depois de gravar a chave (passo 1), `./deploy/publish.ps1 -Domain suporte.SEUDOMINIO -RepoUrl https://github.com/USUARIO/REPO.git -RepoSubdir submissions/seu-nome` faz os passos 2 a 4: sobe a stack, mostra o IP para o Cloudflare, espera o DNS e confere a apresentação e o app por HTTPS.

## Passo a passo

1. **Chave da Anthropic, criada no console da Anthropic com teto de gasto de US$ 10.** Grave direto no SSM. A chave não passa por arquivo nem por chat; o comando pede o valor sem ecoar:

   ```bash
   read -rs KEY && aws ssm put-parameter --name /g4-support/anthropic-api-key --type SecureString --value "$KEY" && unset KEY
   ```

2. **Subir a infraestrutura:**

   ```bash
   aws cloudformation deploy --stack-name g4-support --template-file infra/cloudformation.yaml --capabilities CAPABILITY_IAM --parameter-overrides Domain=suporte.SEUDOMINIO RepoUrl=https://github.com/USUARIO/REPO.git RepoSubdir=.
   ```

   Se o código estiver dentro da pasta de submissão do fork, use `RepoSubdir=submissions/seu-nome`.

   **Antes de ter domínio e repositório público:** `Domain=:80` serve só por HTTP no Elastic IP, e `RepoUrl` aceita um link pré-assinado (expira em 1 h) para um `git bundle` num bucket S3 privado. Foi assim que a primeira versão subiu. O bundle é apagado do bucket assim que a VM clona. Depois, com o domínio, troque `DOMAIN` no `.env` da instância e reinicie o serviço.

3. **DNS no Cloudflare:** registro `A` de `suporte` para o `PublicIp` do output da stack. Funciona com o proxy desligado (DNS only) ou ligado; ligado, use o modo SSL **Full (strict)**. O Caddy emite o certificado Let's Encrypt pelo desafio HTTP-01 na porta 80, que o Cloudflare repassa à VM.

   ```bash
   aws cloudformation describe-stacks --stack-name g4-support --query "Stacks[0].Outputs"
   ```

4. **Verificar:** `https://suporte.SEUDOMINIO` abre a apresentação e `/app/` abre o protótipo. O certificado sai em 1 a 2 minutos depois que o DNS propaga.

5. **Link do repositório na apresentação:** preencha `<meta name="repo-url">` em `presentation/index.html` com a URL do repositório.

## Operação

- Atualizar: `aws ssm start-session --target <instância>`, depois `sudo -u g4 /home/g4/repo/deploy/start.sh --pull`.
- Logs: `docker compose logs -f app`.
- Trocar a chave: repetir o passo 1 com `--overwrite` e reiniciar com `sudo systemctl restart g4-support`.
- Desligar tudo: `aws cloudformation delete-stack --stack-name g4-support`. O parâmetro SSM é removido à parte.

## Proteções de custo

- Na Anthropic: teto de gasto no console (US$ 10 combinados).
- No app: até `LLM_MAX_CALLS_PER_SESSION` análises por visita e `LLM_MAX_CALLS_PER_DAY` por dia; respostas repetidas saem do cache.
- Na AWS: recomenda-se um alerta de orçamento (AWS Budgets) em US$ 15/mês.

## Riscos aceitos

- A imagem base (python:3.12-slim, Debian 13) tem vulnerabilidades altas sem correção publicada em pacotes como `util-linux` e `mount`. O app não usa essas ferramentas e o contêiner roda sem root, com filesystem somente leitura, sem capabilities e sem escalada de privilégio. A CI reconstrói e roda o Trivy e falha se surgir uma vulnerabilidade crítica com correção (a CI em `.github/workflows/ci.yml` repete esses passos quando esta pasta roda como repositório próprio; dentro do repositório do desafio, o GitHub só executa workflows da raiz, então ali ela não roda).
- O LLM pode ser influenciado pelo texto do ticket; por isso não tem ferramentas, a saída tem schema fixo, a regra decide o destino e nenhum rascunho sai sem uma pessoa.

## O que já foi validado e o que não

- `cfn-lint` passa no template, e `bash -n` no script.
- A CI (`.github/workflows/ci.yml`) constrói a imagem e checa o healthcheck do contêiner quando a pasta roda como repositório próprio.
- A imagem e a stack completa (Caddy + app, com o volume de estado) rodaram localmente no Docker em 19/10, com as mesmas restrições de produção.
- Em 19/10 a stack foi criada de verdade em us-east-1 (`t4g.small` com Elastic IP). A apresentação e o app responderam pelo IP público, com os arquivos internos dando 404. Uma chamada real ao Claude Haiku 5.5, feita de dentro do contêiner, levou 7,9 s (1.111 tokens de entrada e 495 de saída).
- Em 19/10 o domínio `g4.bernardomeirelescorrea.com.br` passou a apontar para a VM, com o proxy do Cloudflare ligado. O Caddy obteve o certificado Let's Encrypt pelo desafio HTTP-01 através do proxy. HTTP redireciona para HTTPS (308), os cabeçalhos de segurança chegam ao navegador, os arquivos internos dão 404 e o app (WebSocket) funciona pelo proxy.
- **Ajuste recomendado no Cloudflare:** versão mínima de TLS 1.2 (o padrão da borda ainda aceita TLS 1.0).
