# Publica a stack na AWS e confere o site. Uso (PowerShell, depois de `aws login`):
#   ./deploy/publish.ps1 -Domain suporte.seudominio.com -RepoUrl https://github.com/USUARIO/REPO.git -RepoSubdir submissions/seu-nome
# Pré-requisitos: a chave da Anthropic já gravada no SSM (ver deploy/README.md) e o repositório público.
param(
    [Parameter(Mandatory = $true)][string]$Domain,
    [Parameter(Mandatory = $true)][string]$RepoUrl,
    [string]$RepoSubdir = ".",
    [string]$RepoBranch = "main",
    [ValidateSet("t4g.micro", "t4g.small", "t4g.medium")][string]$InstanceType = "t4g.small",
    [string]$StackName = "g4-support",
    [string]$KeyParameter = "/g4-support/anthropic-api-key"
)
$ErrorActionPreference = "Stop"
$template = Join-Path $PSScriptRoot "..\infra\cloudformation.yaml"

Write-Host "1/4 Conferindo acesso à AWS e a chave no SSM (sem ler o valor)..."
aws sts get-caller-identity --query Account --output text | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Sem sessão na AWS. Rode 'aws login' e tente de novo." }
aws ssm describe-parameters --parameter-filters "Key=Name,Values=$KeyParameter" --query "Parameters[0].Name" --output text | Tee-Object -Variable found | Out-Null
if ($found -ne $KeyParameter) { throw "Parâmetro $KeyParameter não existe. Grave a chave com o comando do deploy/README.md." }

Write-Host "2/4 Subindo a infraestrutura ($InstanceType)..."
aws cloudformation deploy --stack-name $StackName --template-file $template --capabilities CAPABILITY_IAM `
    --parameter-overrides "Domain=$Domain" "RepoUrl=$RepoUrl" "RepoSubdir=$RepoSubdir" "RepoBranch=$RepoBranch" "InstanceType=$InstanceType" "AnthropicKeyParameter=$KeyParameter"
if ($LASTEXITCODE -ne 0) { throw "Falha no CloudFormation; veja os eventos da stack $StackName no console." }
$ip = aws cloudformation describe-stacks --stack-name $StackName --query "Stacks[0].Outputs[?OutputKey=='PublicIp'].OutputValue" --output text

Write-Host ""
Write-Host "3/4 No Cloudflare, crie o registro:  A  $($Domain.Split('.')[0])  ->  $ip   (proxy DESLIGADO, 'DNS only')"
Write-Host "    Esperando o DNS apontar para $ip ..."
for ($i = 0; $i -lt 90; $i++) {
    $resolved = (Resolve-DnsName $Domain -Type A -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress }).IPAddress
    if ($resolved -contains $ip) { break }
    Start-Sleep -Seconds 20
}
if (-not ($resolved -contains $ip)) { throw "O DNS ainda não aponta para $ip. Confira o registro e rode só a etapa 4 depois." }

Write-Host "4/4 Esperando o certificado e os contêineres (a primeira subida leva alguns minutos)..."
foreach ($path in "/", "/app/_stcore/health") {
    $ok = $false
    for ($i = 0; $i -lt 45; $i++) {
        try { $r = Invoke-WebRequest -Uri "https://$Domain$path" -UseBasicParsing -TimeoutSec 15; if ($r.StatusCode -eq 200) { $ok = $true; break } } catch { }
        Start-Sleep -Seconds 20
    }
    if (-not $ok) { throw "https://$Domain$path não respondeu. Logs: aws ssm start-session e 'docker compose logs'." }
    Write-Host "    ok  https://$Domain$path"
}
Write-Host ""
Write-Host "Publicado: https://$Domain  (apresentação)  e  https://$Domain/app/  (protótipo)"
