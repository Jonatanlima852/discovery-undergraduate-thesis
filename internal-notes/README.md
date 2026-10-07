# Notas internas de implementação

Este diretório reúne o histórico de aprendizado, planejamento e acompanhamento
do projeto. Foi renomeado de `docs/` para `internal-notes/`; referências antigas
a `docs/` nos registros históricos se referem a este acervo. O conteúdo abaixo
preserva o contexto em que foi escrito e pode descrever etapas já superadas.

A documentação pública atual começa em [docs/README.md](../docs/README.md).
Notas que já eram versionadas continuam no Git; a regra de ignore mantém
novas notas locais fora do versionamento por padrão.

## Apresentação histórica

This repository contains the reference implementation for a graduation thesis project on interoperable cooperation among heterogeneous intelligent agents.

The project proposes, implements, and evaluates an interoperability contract for agents with different internal architectures, especially BDI agents and LLM-based agents. The contract is supported by a distributed runtime responsible for discovery, messaging, orchestration, health monitoring, failure detection, and task reassignment.

## Core idea

The runtime does not try to replace agent reasoning. Instead, it provides a common operational layer so that different agents can cooperate through the same protocol.

The main separation is:

```text
Runtime
  discovery
  orchestration
  task lifecycle
  messaging
  failure detection
  observability

Agent
  domain reasoning
  plan execution
  BDI deliberation
  LLM reasoning
  tool usage
```

## Main components

```text
registry-service
orchestrator-service
messaging-service
failure-detector
observability/event-log
python-sdk
mock-agents
bdi-agent
llm-agent
```

## Recommended implementation order

```text
1. Define contract v0.1
2. Write .proto files
3. Implement registry-service
4. Implement orchestrator-service with FIRST_AVAILABLE policy
5. Implement mock agents
6. Add Docker Compose
7. Implement Python SDK
8. Implement simplified BDI agent
9. Add messaging-service
10. Add LLM planner/explainer agent
11. Add heartbeat and failure detection
12. Add task reassignment
13. Add observability events
14. Run benchmarks
15. Freeze contract v1.0
```

## Documentation map

| File | Purpose |
|---|---|
| `01-project-scope.md` | Project scope, boundaries, and contribution |
| `02-contract-specification.md` | Contract entities and fields |
| `03-architecture.md` | Runtime architecture and component responsibilities |
| `04-orchestrator-design.md` | How orchestration works and why it is not fully LLM-based |
| `05-python-sdk-plan.md` | Python SDK design and expected developer experience |
| `06-agent-models.md` | Mock, BDI, and LLM agent roles |
| `07-messaging-and-failures.md` | Messaging, heartbeat, failure detection, and reassignment |
| `08-benchmarks-and-evaluation.md` | Metrics, scenarios, and expected experiments |
| `09-implementation-roadmap.md` | Step-by-step technical roadmap |
| `10-repo-structure.md` | Suggested repository organization |
| `11-decisions-and-tradeoffs.md` | Design decisions and trade-offs |
| `12-definition-of-done.md` | Completion criteria for each phase |
| `13-runbook-execucao-e-testes-manuais.md` | Como subir, testar manualmente, coletar métricas e encerrar o sistema |
| `implementation/phase-16-logistics-golden-benchmark.md` | Método e resultados do benchmark LLM-only, BDI-only e híbrido |

## Current evaluation extension

The implementation roadmap is complete. The central heterogeneous-agent
evaluation is documented in
`implementation/phase-16-logistics-golden-benchmark.md`: a constrained
logistics domain compares LLM-only, BDI-only, and LLM + BDI against an
independent action simulator.
