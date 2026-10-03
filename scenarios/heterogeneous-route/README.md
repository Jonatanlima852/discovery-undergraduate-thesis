# Cenário heterogêneo de rotas

Topologia isolada para o fluxo transitório `LLM -> BDI -> LLM`. Execute os
comandos a partir da raiz do repositório.

## Configuração

Copie o exemplo e preencha a chave localmente:

```sh
cp scenarios/heterogeneous-route/.env.example \
  scenarios/heterogeneous-route/.env
```

Variáveis:

| Variável | Uso | Default |
|---|---|---:|
| `OPENAI_API_KEY` | credencial da Responses API; obrigatória | — |
| `LLM_MODEL` | modelo usado pelo agente LLM | `gpt-5.6-luna` |
| `REGISTRY_PORT` | Registry no host | `50051` |
| `ORCHESTRATOR_PORT` | Orchestrator no host | `50052` |
| `BDI_AGENT_PORT` | agente BDI no host | `60054` |
| `LLM_AGENT_PORT` | agente LLM no host | `60056` |

O arquivo `.env` é ignorado pelo Git. Nunca coloque a chave no Compose,
Dockerfile ou relatório do cenário.

## Execução

```sh
docker compose \
  --env-file scenarios/heterogeneous-route/.env \
  -f scenarios/heterogeneous-route/compose.yaml \
  up --build -d --wait

ORCHESTRATOR_ADDR=localhost:50052 \
uv run --directory clients/submit-task \
  python ../../scenarios/heterogeneous-route/scenario.py
```

O relatório é salvo em `experiments/results/heterogeneous-report.json`.

## Logs e limpeza

```sh
docker compose \
  --env-file scenarios/heterogeneous-route/.env \
  -f scenarios/heterogeneous-route/compose.yaml logs -f

docker compose \
  --env-file scenarios/heterogeneous-route/.env \
  -f scenarios/heterogeneous-route/compose.yaml down
```

Use `down -v` somente quando também quiser apagar os eventos. O nome de
projeto `tg-heterogeneous-route` mantém rede e volume separados do Compose
baseline em `infra/`.

O encadeamento das três tasks ainda acontece no adaptador Python. A fase 12E
o moverá para o Orchestrator; a topologia do cenário continuará válida.
