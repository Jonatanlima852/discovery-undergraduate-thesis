# Fase 11 — Políticas de seleção

Status: concluída em 2026-10-03.

## Objetivo

Completar as políticas declaradas no contrato e preparar o cenário B dos
benchmarks sem alterar o baseline determinístico `FIRST_AVAILABLE`.

## Implementação

O `selection.Selector` é compartilhado pelo `execution.Executor` e seleciona
somente entre os agentes compatíveis e vivos devolvidos pelo Registry:

- `FIRST_AVAILABLE`: mantém o primeiro agente da ordem estável do Registry;
- `ROUND_ROBIN`: mantém um cursor concorrente por conjunto de agentes e percorre
  esse conjunto em ordem de `agent_id`;
- `LEAST_LOADED`: compara `load`, depois `current_task_count` e finalmente
  `agent_id`, garantindo desempate reproduzível;
- `RANDOM`: preserva a quarta opção já existente no contrato.

O heartbeat já transportava carga, mas ela ficava apenas no estado interno do
Registry. `AgentDescriptor` agora expõe `current_task_count` e `load`, atualizados
em cada heartbeat e retornados pela descoberta. Isso permite que
`LEAST_LOADED` use estado operacional real.

O SDK `Task`, `Scenario.submit()` e os steps de `submit_workflow()` aceitam
`selection_policy`. O cliente de terminal aceita `--selection-policy` com os
valores `first-available`, `round-robin`, `least-loaded` e `random`.

## Invariantes verificadas

- o valor protobuf padrão continua significando `FIRST_AVAILABLE`;
- round-robin distribui sequências de forma uniforme e é seguro sob chamadas
  concorrentes;
- alterações na ordem de entrada não tornam o round-robin não determinístico;
- least-loaded usa os dois sinais de carga e desempata por ID;
- retry e exclusão de agente continuam sendo aplicados antes da seleção;
- o estado recebido no heartbeat chega ao descriptor descoberto;
- políticas são preservadas no round-trip da API pública Python.

## Validação

Os testes Go com race detector cobrem seleção, integração com o executor e
propagação do heartbeat pelo Registry. A suíte Python cobre o modelo público e
o envio pelo `Scenario`.

Próximo incremento: automatizar e executar os benchmarks A-E, salvando dados
brutos, sumários, gráficos e instruções reproduzíveis.
