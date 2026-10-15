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

3. **DNS no Cloudflare:** registro `A` de `suporte` para o `PublicIp` do output da stack, com **proxy desligado (DNS only)**, para o Caddy emitir o certificado Let's Encrypt.

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

## O que já foi validado e o que não

- `cfn-lint` passa no template, e `bash -n` no script.
- A CI (`.github/workflows/ci.yml`) constrói a imagem e checa o healthcheck do contêiner a cada push.
- **Não validado ainda:** a criação real da stack, a emissão do certificado e a chamada à API da Anthropic. Isso só acontece no primeiro deploy, que depende do domínio e da chave.
