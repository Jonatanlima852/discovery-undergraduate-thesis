# Fase 13 — Benchmarks A-E

Status: concluída em 2026-10-03.

## Entrega reproduzível

`benchmarks/run.sh` executa uma topologia Docker isolada e produz uma pasta
datada em `benchmarks/results/`. A topologia contém agentes dedicados para que
as capabilities de um cenário não interfiram nas de outro.

Artefatos produzidos:

- `events.jsonl`: eventos brutos correlacionados;
- `results.json`: amostras e agregados observados pelo cliente;
- `summary.csv`: comparação dos cenários e políticas;
- `task-summary.csv`: latências, recuperação e reassignment por task;
- `latency.svg`: latência média por caso;
- `agent-distribution.svg`: distribuição das políticas entre agentes;
- `recovery.svg`: recuperação e latência total com falha;
- `message-count.svg`: ausência de envelopes na arquitetura atual.

O script encerra os contêineres automaticamente, inclusive quando ocorre erro.
A chave da OpenAI é lida do `.env` e nunca é copiada para os resultados.

## Cenários automatizados

- A: 10 tasks básicas contra um único agente compatível;
- B: 12 tasks para cada política sobre três agentes compatíveis;
- C: uma pergunta natural executando o workflow LLM -> BDI -> LLM;
- D: timeout no primeiro agente e reassignment para o segundo;
- E: task BDI estruturada comparada ao workflow assistido por LLM.

Os cenários mais baratos possuem várias amostras. C, D e E usam uma amostra
por execução padrão por envolverem custo externo ou uma falha controlada; novas
execuções datadas permitem ampliar a amostra usada na monografia.

## Execução de referência

Execução integrada `20261003T220244Z`:

| Caso | Sucesso | Latência média | Evidência principal |
|---|---:|---:|---|
| A | 100% (10/10) | 82,9 ms | `basic-agent` executou todas |
| B FIRST_AVAILABLE | 100% (12/12) | 52,3 ms | 12 tasks em `policy-a` |
| B ROUND_ROBIN | 100% (12/12) | 55,3 ms | distribuição 4/4/4 |
| B LEAST_LOADED | 100% (12/12) | 49,7 ms | 12 tasks em `policy-b` (load 0,1) |
| C | 100% (1/1) | 9.919,3 ms | dois steps, BDI e LLM, explicação presente |
| D | 100% (1/1) | 210,1 ms | um reassignment; recovery 10,7 ms |
| E estruturado | 100% (1/1) | 15,8 ms | execução direta no BDI |
| E assistido | 100% (1/1) | 7.107,4 ms | overhead observado de 7.091,6 ms |

O sumário derivado de eventos reconhece tanto `TASK_COMPLETED` quanto
`WORKFLOW_COMPLETED`: foram 50 raízes e 50 conclusões (100%). O p95 agregado
foi 384,1 ms; os workflows LLM são outliers intencionais e aparecem separados
no CSV e no gráfico.

## Interpretação

Os resultados confirmam as hipóteses do documento de avaliação:

- `FIRST_AVAILABLE` concentra trabalho;
- `ROUND_ROBIN` distribui uniformemente;
- `LEAST_LOADED` segue a carga reportada;
- o runtime recupera uma task quando retry e exclusão estão habilitados;
- a decomposição LLM viabiliza cooperação heterogênea, mas adiciona segundos de
  latência em relação à task estruturada.

`message_count` permanece zero: estes workflows usam chamadas diretas ao
`AgentService`, sem um Messaging Service. Essa evidência alimenta a decisão de
mensageria do próximo incremento.

Próximo incremento: registrar a decisão arquitetural sobre mensageria com base
nos cenários executados e alinhar contrato, escopo e limitações.
