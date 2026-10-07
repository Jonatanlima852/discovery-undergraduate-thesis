# Cenário de mensageria básica

Valida o caminho mínimo `agent-a -> MessagingService -> agent-b`, incluindo
payload, conversation, correlation, trace, task e TTL.

```sh
docker compose -f scenarios/messaging-basic/compose.yaml up --build -d --wait

PYTHONPATH=sdk/python/src \
uv run --directory clients/submit-task \
  python ../../scenarios/messaging-basic/scenario.py

docker compose -f scenarios/messaging-basic/compose.yaml down
```

O cenário deve terminar com `CENÁRIO APROVADO`. O broker é em memória e possui
semântica at-most-once; mensagens pendentes não sobrevivem a reinício.

[Catálogo de cenários](../../docs/scenarios.md)
