# Workflow sequencial explícito

Valida o primeiro incremento do engine de workflows sem LLM ou bindings:

```text
SubmitWorkflow
  first (echo)
    -> second (echo)
      -> WorkflowResult.output
```

```sh
docker compose -f scenarios/workflow-sequential/compose.yaml \
  up --build -d --wait

uv run --directory sdk/python python \
  ../../scenarios/workflow-sequential/scenario.py

docker compose -f scenarios/workflow-sequential/compose.yaml down -v
```

O resultado esperado é `CENÁRIO APROVADO`. Os eventos no volume do
Orchestrator permitem reconstruir workflow, run, steps e tasks materializadas.

`down -v` apaga o volume de eventos deste cenário. Para preservá-lo, omita `-v`.

[Catálogo de cenários](../../docs/scenarios.md)
