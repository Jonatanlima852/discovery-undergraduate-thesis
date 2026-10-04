# Saídas de referência

Uma execução básica bem-sucedida termina de forma equivalente a:

```text
Resultado:
  status   : COMPLETED
  agent_id : mock-agent-01
  output   : {"echo": "Teste ponta a ponta"}
```

Na execução de benchmarks registrada em 3 de outubro de 2026, os cenários A-E
foram concluídos. Entre os resultados observados: 10/10 execuções básicas com
sucesso, distribuição round-robin 4/4/4, recuperação após falha em 10,7 ms e
100% dos workflows raiz concluídos. Os valores são evidência de uma execução,
não garantias de desempenho para outras máquinas.

Os artefatos completos de cada nova execução são gravados em
`benchmarks/results/<timestamp>/` e incluem o resumo CSV, eventos JSONL e os
gráficos gerados.
