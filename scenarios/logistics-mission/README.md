# Missão logística LLM + BDI

O exemplo recebe linguagem natural, usa a LLM somente para extrair as
restrições e entrega a missão estruturada ao agente BDI. O BDI encontra uma
sequência determinística e um simulador independente confirma precondições,
energia, prazo, locais obrigatórios/proibidos e estado final.

Na raiz do repositório:

```sh
docker compose --env-file .env -f benchmarks/compose.yaml up \
  --build -d --wait registry orchestrator bdi-agent llm-agent

PYTHONPATH=sdk/python/src \
  uv run --directory clients/submit-task \
  python scenarios/logistics-mission/scenario.py

docker compose --env-file .env -f benchmarks/compose.yaml down
```

O caso demonstrado exige entrega em H, passagem por D, proíbe C, estabelece
reserva mínima de bateria e deadline. O comando falha se o plano produzido não
passar no oráculo determinístico.
