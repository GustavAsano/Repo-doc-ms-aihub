#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
command -v docker >/dev/null || { echo "Docker nao encontrado." >&2; exit 1; }
docker compose version >/dev/null

# Cria .env.secrets com template se nao existir ou estiver vazio
if [[ ! -f .env.secrets ]] || [[ ! -s .env.secrets ]]; then
  cat > .env.secrets << 'EOF'
# =============================================================================
# .env.secrets — credenciais e configurações locais (nunca vai ao git)
# Preencha apenas as variáveis do provedor LLM que for usar.
# =============================================================================

# AWS Bedrock (deixe vazios se usar role IAM da EC2)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_SESSION_TOKEN=
AWS_REGION=us-east-1
BEDROCK_REGION=us-east-1

# Google Gemini — https://aistudio.google.com/app/apikey
GOOGLE_API_KEY=

# OpenAI — https://platform.openai.com/api-keys
OPENAI_API_KEY=

# Chave que protege os endpoints do backend (qualquer string aleatória)
API_KEY=

# Porta do frontend no host (default: 3001)
UI_PORT=3001
EOF
  echo "Arquivo .env.secrets criado com template. Preencha as variaveis antes de continuar." >&2
  exit 1
fi
compose=(docker compose --env-file .env.secrets)
case "${1:-}" in
  --down) "${compose[@]}" down ;;
  --dev) "${compose[@]}" -f dev.docker-compose.yml up --build ;;
  "") "${compose[@]}" up --build -d ;;
  *) echo "Uso: $0 [--dev|--down]" >&2; exit 1 ;;
esac
