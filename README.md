# TG Runtime

Runtime e SDK para cooperação entre agentes inteligentes heterogêneos,
especialmente agentes BDI e agentes baseados em LLM.

O contrato comum cuida de descoberta, submissão de tasks, resultados,
healthcheck e rastreabilidade. A arquitetura interna de cada agente continua
livre.

## Experiência de desenvolvimento pretendida

Agentes Python devem ser classes pequenas fornecidas pelo `sdk/python`:

```python
from tg_sdk import BdiAgent, LlmAgent


class RouteAgent(BdiAgent):
    capabilities = ["route-planning"]
    # declara crenças, desejo e planos


class PlannerAgent(LlmAgent):
    capabilities = ["task-decomposition"]
    # declara prompt e schema de saída
```

As classes do SDK escondem protobuf, gRPC, registro, heartbeat, conversão de
payload, montagem de resultados e integração com a OpenAI Responses API.

Um cenário integrado deve declarar seus agentes em um arquivo Python simples,
subir uma topologia Docker Compose isolada e enviar somente a pergunta inicial
ao runtime. Registry e orchestrator descobrem os agentes conectados e
coordenam o trabalho.

## Estado atual

O repositório já contém:

- contrato protobuf compartilhado;
- Registry e Orchestrator em Go;
- SDK Python com `Agent` e uma primeira versão de `BdiAgent`;
- agentes mock, BDI e LLM;
- demo heterogênea LLM → BDI → LLM;
- heartbeat, detecção de falhas e log de eventos.

A próxima evolução planejada é transformar as abstrações BDI e LLM em APIs
públicas e amigáveis do SDK e introduzir cenários Python de um arquivo com
infraestrutura própria.

Consulte:

- `docs/README.md` para o mapa completo da documentação;
- `docs/05-python-sdk-plan.md` para a API pretendida do SDK;
- `docs/implementation/phase-12d-sdk-agent-authoring-and-scenarios.md` para o
  plano detalhado de implementação;
- `docs/13-runbook-execucao-e-testes-manuais.md` para executar o estado atual.

## Execução atual

Baseline:

```sh
make up

uv run --directory clients/submit-task python main.py \
  --goal "Teste ponta a ponta" \
  --capability echo
```

Cenário heterogêneo isolado:

```sh
docker compose \
  --env-file scenarios/heterogeneous-route/.env \
  -f scenarios/heterogeneous-route/compose.yaml \
  up --build -d --wait

uv run --directory clients/submit-task \
  python ../../scenarios/heterogeneous-route/scenario.py
```
