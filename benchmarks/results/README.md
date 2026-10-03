# Resultados dos benchmarks

`./benchmarks/run.sh` cria uma pasta datada contendo:

- `events.jsonl`: eventos brutos do Orchestrator;
- `results.json`: resultados e medições do cliente para A-E;
- `summary.csv`: uma linha agregada por cenário/caso;
- `task-summary.csv`: métricas derivadas dos eventos por task;
- `latency.svg`: comparação visual das latências médias;
- `agent-distribution.svg`: distribuição por política e agente;
- `recovery.svg`: tempo de recuperação e latência total com falha;
- `message-count.svg`: contagem de envelopes (zero na arquitetura atual).

As execuções são ignoradas pelo Git para evitar misturar resultados locais e
credenciais indiretas com o código. Resultados escolhidos para a monografia
devem ser copiados conscientemente para o artefato de avaliação.
