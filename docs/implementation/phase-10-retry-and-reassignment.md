# Fase 10 — Timeout, retry e reassignment

## Objetivo

Recuperar uma task quando o agente selecionado falha ou ultrapassa o timeout,
sem transferir a política operacional para o agente.

## Decisões

- `RetryPolicy.max_attempts` conta tentativas totais, incluindo a primeira;
- ausência de policy mantém uma única tentativa, preservando o baseline;
- `Task.deadline_ms` representa timeout por tentativa;
- quando `deadline_ms` é zero, usa-se `EXECUTION_TIMEOUT` do Orchestrator
  (`30s` por default);
- com `exclude_failed_agent=true`, o agente anterior é removido dos candidatos;
- cada tentativa redescobre os agentes no Registry;
- descoberta é ordenada por `agent_id`, tornando `FIRST_AVAILABLE`
  determinístico e reproduzível;
- falhas não retryable retornadas pelo agente encerram imediatamente a task.

## Estrutura

O fluxo saiu do handler gRPC e passou para
`orchestrator/internal/execution.Executor`, com interfaces para descoberta,
execução remota e eventos. O mesmo executor será usado pelos steps de workflow
na Fase 12E.

## Eventos

```text
TASK_ASSIGNED     primeira tentativa
TASK_TIMEOUT      tentativa excedeu o limite
TASK_FAILED       RPC ou TaskResult falhou
TASK_REASSIGNED   nova tentativa após redescoberta
TASK_COMPLETED    resultado terminal bem-sucedido
```

Todos carregam `task_id`, `trace_id`, `agent_id`, timestamp e tentativa em
`details`. O intervalo `TASK_TIMEOUT -> TASK_REASSIGNED` permite calcular o
tempo de recuperação.

## Progresso

Atualizado em 2026-10-03.

```text
TaskExecutor extraído                    CONCLUÍDO
timeout por tentativa                    CONCLUÍDO
RetryPolicy e backoff                    CONCLUÍDO
exclusão e redescoberta                  CONCLUÍDO
eventos de timeout/reassignment          CONCLUÍDO
testes unitários determinísticos         CONCLUÍDO
cenário integrado de falha               CONCLUÍDO
métricas de recovery/reassignment        CONCLUÍDO
```

## Validação realizada

Em 2026-10-03, o cenário Docker isolado executou:

```text
TASK_ASSIGNED   agent=a-slow    attempt=1
TASK_TIMEOUT    agent=a-slow    attempt=1
TASK_REASSIGNED agent=b-healthy attempt=2
TASK_COMPLETED  agent=b-healthy attempt=2
```

O timeout configurado foi `100 ms`. O intervalo observado entre
`TASK_TIMEOUT` e `TASK_REASSIGNED` foi aproximadamente `12,18 ms`. O cliente
recebeu `TASK_STATUS_COMPLETED` de `b-healthy`. Todos os serviços estavam
saudáveis e o cenário foi removido com seu volume após a verificação.

Também passaram os testes do runtime, quatro testes unitários específicos do
executor, dezenove testes do SDK e o teste das métricas de recuperação.

## Estado e próximo passo

A definição de pronto da Fase 10 foi atendida. O próximo incremento é a Fase
12E.1: consolidar o `TaskExecutor` recém-extraído como unidade reutilizável e
iniciar o contrato experimental de workflows, com decisões abertas registradas
antes da alteração do protobuf.
