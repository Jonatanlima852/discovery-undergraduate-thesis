# Cenário heterogêneo LLM + BDI

Este cenário usa a API pública `tg_sdk.Scenario` para executar três tasks
correlacionadas:

```text
LLM decompõe -> BDI planeja rota -> LLM explica
```

Suba os serviços:

```sh
docker compose --env-file .env \
  -f infra/docker-compose.yml \
  --profile heterogeneous \
  up --build -d
```

Execute:

```sh
uv run --directory clients/submit-task \
  python ../../examples/demo_scenario/heterogeneous_demo.py
```

O cenário aprova somente se o BDI selecionar `via_intermediate`,
retornar a rota `A -> B -> D` e distância `25`.

O arquivo do cenário trabalha apenas com valores Python. Construção de
protobuf, IDs, trace compartilhado, conexão gRPC e submissão ao orchestrator
ficam encapsulados pelo SDK.

O encadeamento das três etapas ainda ocorre no cliente porque o orchestrator
atual executa uma task por chamada. Quando houver suporte a workflows, o
cenário continuará enviando apenas a pergunta inicial e o adaptador transitório
poderá ser removido sem alterar as classes dos agentes.
