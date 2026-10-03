# TG Runtime

Guia rápido para executar o projeto. Rode todos os comandos a partir da raiz
do repositório.

## Pré-requisitos

- Docker com Docker Compose v2;
- Python 3.11 ou superior;
- [`uv`](https://docs.astral.sh/uv/);
- Go 1.22 ou superior, apenas para build e testes locais.

Os stubs protobuf já estão versionados; não é necessário regenerá-los para a
execução normal.

## Execução básica

Suba o runtime e o agente de exemplo:

```sh
make up
```

Envie uma tarefa:

```sh
uv run --directory clients/submit-task python main.py \
  --goal "Teste ponta a ponta" \
  --capability echo
```

O resultado esperado contém `status: COMPLETED` e
`agent_id: mock-agent-01`.

Para acompanhar os logs e encerrar:

```sh
make logs
make down
```

## Cenários

Cada cenário possui uma topologia Docker isolada e instruções próprias:

- [workflow sequencial](scenarios/workflow-sequential/README.md);
- [timeout e reassignment](scenarios/failure-reassignment/README.md);
- [cooperação LLM + BDI](scenarios/heterogeneous-route/README.md).

O cenário LLM + BDI exige uma chave da OpenAI. Antes de executá-lo:

```sh
cp scenarios/heterogeneous-route/.env.example \
  scenarios/heterogeneous-route/.env
```

Preencha `OPENAI_API_KEY` no arquivo criado. O `.env` local não deve ser
versionado.

## Verificação local

```sh
make build
make test
uv run --directory sdk/python --with pytest pytest -q
```

Para validar apenas os arquivos Docker Compose:

```sh
docker compose -f infra/docker-compose.yml config --quiet
docker compose -f scenarios/workflow-sequential/compose.yaml config --quiet
docker compose -f scenarios/failure-reassignment/compose.yaml config --quiet
docker compose \
  --env-file scenarios/heterogeneous-route/.env \
  -f scenarios/heterogeneous-route/compose.yaml config --quiet
```

## Comandos úteis

```sh
make help       # lista os comandos disponíveis
make up         # constrói e inicia a execução básica
make logs       # acompanha os logs
make down       # encerra a execução básica
make build      # compila os serviços Go
make test       # executa os testes Go
make proto      # regenera os stubs após mudanças no contrato
```
