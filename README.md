# Repo-doc

AI-powered documentation generator for code repositories. Analyzes source code using LLMs and produces a full MkDocs documentation site with technical and/or functional documentation.

## Features

- **Repository loading** — via Git URL, ZIP upload, or local folder path
- **Documentation modes** — Technical only, Functional only, or both
- **Multiple LLM providers** — Gemini, OpenAI, AWS Bedrock
- **Multi-language output** — PT-BR, EN-US, ES-ES, FR-FR, DE-DE
- **MkDocs site** — live preview of the generated docs inside the UI
- **Code graph** — visual dependency/import graph for the analyzed repo
- **AI Chat** — ask questions about the repository based on the generated docs
- **Export** — download documentation as PDF or DOCX
- **Library** — save and reload previously generated documentation

## Architecture

| Service | Technology | Internal Port |
|---|---|---|
| Backend | FastAPI (Python) | 8000 |
| Frontend | Vue 3 + Vuetify, served by nginx | 3000 (host: 3001) |

Both services run as Docker containers managed by Docker Compose.

## Requirements

- Docker and Docker Compose
- A `.env.secrets` file (see below)

## Setup

Run `./run.sh` once — if `.env.secrets` doesn't exist or is empty, it will be created automatically with a template. Fill in the credentials for the LLM provider you want to use and run again.

Variables in `.env.secrets`:

| Variable | Description |
|---|---|
| `AWS_ACCESS_KEY_ID` | AWS key (leave empty if using EC2 IAM role) |
| `AWS_SECRET_ACCESS_KEY` | AWS secret |
| `AWS_SESSION_TOKEN` | AWS session token (optional) |
| `AWS_REGION` | AWS region (default: `us-east-1`) |
| `BEDROCK_REGION` | Bedrock region (default: `us-east-1`) |
| `GOOGLE_API_KEY` | Gemini API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `API_KEY` | Any random string to protect backend endpoints |
| `UI_PORT` | Host port for the frontend (default: `3001`) |

## Running

```bash
# Production (detached)
./run.sh

# Development (with live reload, attached)
./run.sh --dev

# Stop and remove containers
./run.sh --down
```

The UI will be available at `http://localhost:3001`.

## Usage

1. **Home** — configure the LLM provider and model, then load a repository (Git URL, ZIP, or local path)
2. **Graph** — explore the code dependency graph
3. **Sections** — customize which documentation sections to generate and their descriptions
4. **Run** — trigger documentation generation and follow the progress stream
5. **Docs** — preview the generated MkDocs site inline
6. **Chat** — ask questions about the repository

## LLM Providers

| Provider | Supported Models |
|---|---|
| Gemini | gemini-2.5-flash, gemini-2.5-pro, gemini-2.0-flash, gemini-2.0-pro |
| OpenAI | gpt-4o, gpt-4o-mini, gpt-5-mini, gpt-5-nano |
| AWS Bedrock | Claude Haiku/Sonnet, Amazon Nova, DeepSeek, Kimi, Mistral Devstral, and others |

## Backend API

The FastAPI backend exposes a Swagger UI at `http://localhost:8000/docs/swagger` and ReDoc at `http://localhost:8000/docs`.

Main route groups:

| Prefix | Description |
|---|---|
| `/repo` | Load repositories and manage the library |
| `/docs` | Generate documentation (SSE stream) and serve the MkDocs preview |
| `/llm` | Configure and persist LLM settings |
| `/chat` | AI chat over generated documentation |
| `/graph` | Dependency graph data |
| `/export` | PDF and DOCX export |
