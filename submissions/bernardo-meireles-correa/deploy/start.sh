#!/usr/bin/env bash
# Sobe a stack na EC2. Busca a chave da API no SSM (via papel IAM da instância)
# e grava num tmpfs, fora do disco e do repositório. Uso: deploy/start.sh [--pull]
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] || { echo "Falta .env (copie de .env.example)"; exit 1; }
set -a; . ./.env; set +a

SECRETS_DIR=/run/g4-support
SECRETS_ENV_FILE="$SECRETS_DIR/secrets.env"
sudo install -d -m 700 -o "$(id -u)" "$SECRETS_DIR"

if [ "${LLM_PROVIDER:-off}" = "anthropic" ]; then
  key=$(aws ssm get-parameter --name "${ANTHROPIC_KEY_PARAMETER:?}" --with-decryption \
          --query Parameter.Value --output text)
  umask 077
  printf 'ANTHROPIC_API_KEY=%s\n' "$key" > "$SECRETS_ENV_FILE"
  unset key
else
  : > "$SECRETS_ENV_FILE"
fi
export SECRETS_ENV_FILE

if [ "${1:-}" = "--pull" ]; then git pull --ff-only; fi

docker compose up -d --build --remove-orphans
docker compose ps
