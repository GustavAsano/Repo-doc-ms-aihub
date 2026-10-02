# Execucao na EC2 pelo Remote SSH

O arquivo `.env.secrets` deve ter permissao 600 e esta ignorado pelo Git.
Para Bedrock com role IAM da EC2, deixe AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
e AWS_SESSION_TOKEN vazios. BEDROCK_REGION define a regiao usada pelo aplicativo.
Nenhuma chamada ao Bedrock foi validada neste setup.

```bash
cd /home/ubuntu/Repo-doc
nano .env.secrets
./run.sh
docker compose --env-file .env.secrets ps
docker compose --env-file .env.secrets logs --tail=100
curl http://127.0.0.1:3001/health
```

No VS Code, abra Ports/Portas e encaminhe a porta 3001. Acesse
http://localhost:3001 no navegador local. A API fica disponivel pelo proxy
na mesma porta; Swagger em /docs/swagger.

API_KEY e incluida no frontend e nao implementa autenticacao nas rotas atuais.
O Compose publica a UI somente em 127.0.0.1. Os dados persistem no volume
repo-doc-data; `./run.sh --down` para os servicos sem remover esse volume.

## Bloqueio identificado em 2026-10-01

O disco raiz esta 100% ocupado (15 GB), impedindo o build Docker.
Ha outra instalacao ativa em /home/ubuntu/git/Repo-doc-ms-aihub na porta 3000,
com /health respondendo status ok. Este checkout usa a porta 3001 para evitar
conflito e nao foi iniciado. Libere espaco ou amplie o volume antes de executar
./run.sh novamente. Nenhum container ou volume existente foi removido.
