# Cenário de timeout e reassignment

Este cenário valida deterministicamente a Fase 10:

```text
a-slow recebe a tentativa 1 -> timeout em 100 ms
orchestrator exclui a-slow -> redescobre agentes
b-healthy recebe a tentativa 2 -> COMPLETED
```

O Registry ordena agentes por ID, portanto `a-slow` é selecionado primeiro.

## Executar

```sh
docker compose \
  -f scenarios/failure-reassignment/compose.yaml \
  up --build -d --wait

uv run --directory sdk/python \
  python ../../scenarios/failure-reassignment/scenario.py
```

O resultado esperado contém `CENÁRIO APROVADO agent_id=b-healthy`.

Copie os eventos para medir timeout e recuperação:

```sh
docker compose -f scenarios/failure-reassignment/compose.yaml \
  exec -T orchestrator cat /data/events.jsonl \
  > experiments/results/failure-reassignment-events.jsonl
```

Encerre e remova os artefatos isolados:

```sh
docker compose -f scenarios/failure-reassignment/compose.yaml down -v
```
