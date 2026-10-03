# 09 — Implementation Roadmap

## Purpose

This document is the operational roadmap. Follow it during implementation.

Do not jump to later phases before completing the definition of done for the current phase.

---

# Phase 0 — Repository setup

## Goal

Create a clean repository foundation.

## Tasks

```text
1. Create repository.
2. Add README.md.
3. Add docs/ folder.
4. Add proto/ folder.
5. Add runtime/ folder.
6. Add python-sdk/ folder.
7. Add agents/ folder.
8. Add benchmarks/ folder.
9. Add docker-compose.yml placeholder.
10. Add Makefile placeholder.
```

## Definition of done

```text
repository structure exists
README explains project purpose
all documentation files are committed
```

---

# Phase 1 — Contract v0.1

## Goal

Define the contract before implementing runtime behavior.

## Tasks

```text
1. Create proto/contract/v1/contract.proto.
2. Define AgentDescriptor.
3. Define Capability.
4. Define Task.
5. Define TaskResult.
6. Define TaskEvent.
7. Define HealthStatus.
8. Define ErrorInfo.
9. Define TraceContext.
10. Define RegistryService.
11. Define OrchestratorService.
12. Define AgentService.
13. Generate Go code from proto.
14. Generate Python code from proto.
15. Add validation notes in docs.
```

## Do not implement yet

```text
LLM agent
BDI agent
messaging service
failure detector
advanced policies
```

## Definition of done

```text
.proto compiles
Go stubs are generated
Python stubs are generated
contract entities are documented
```

---

# Phase 2 — Registry service

## Goal

Implement agent registration and discovery.

## Tasks

```text
1. Create runtime/registry-service.
2. Implement RegisterAgent.
3. Implement UnregisterAgent.
4. Implement GetAgent.
5. Implement DiscoverAgents.
6. Store agents in memory.
7. Add filtering by requiredCapabilities.
8. Add basic status update.
9. Add unit tests.
```

## Minimum behavior

```text
agent can register
agent can be retrieved by ID
agents can be discovered by capability
```

## Definition of done

```text
registry starts locally
agent descriptor can be registered
DiscoverAgents returns compatible agents
unit tests pass
```

---

# Phase 3 — Mock agent service

## Goal

Implement a simple agent that can receive a task.

## Tasks

```text
1. Create agents/mock-agent.
2. Implement AgentService.ExecuteTask.
3. Return TaskResult.
4. Add configurable capability.
5. Add configurable delay.
6. Add configurable failure mode.
7. Add manual registration call to Registry.
```

## Definition of done

```text
mock agent starts locally
mock agent registers itself
mock agent executes simple task
mock agent can intentionally fail
```

---

# Phase 4 — Orchestrator service v0.1

## Goal

Implement basic deterministic orchestration.

## Tasks

```text
1. Create runtime/orchestrator-service.
2. Implement SubmitTask.
3. Validate Task.
4. Emit TASK_CREATED.
5. Query Registry.DiscoverAgents.
6. Implement FIRST_AVAILABLE selection.
7. Call selected AgentService.ExecuteTask.
8. Return TaskResult.
9. Emit TASK_ASSIGNED and TASK_COMPLETED.
10. Store events in memory or JSONL.
```

## Definition of done

```text
client submits task to orchestrator
orchestrator discovers agent
orchestrator assigns task
agent completes task
orchestrator returns result
events are recorded
```

---

# Phase 5 — Docker Compose baseline

## Goal

Run the minimum system with one command.

## Services

```text
registry
orchestrator
mock-agent
client-runner
```

## Tasks

```text
1. Create Dockerfile for registry.
2. Create Dockerfile for orchestrator.
3. Create Dockerfile for mock-agent.
4. Create docker-compose.yml.
5. Add Makefile targets.
```

## Suggested Makefile targets

```text
make proto
make build
make up
make down
make logs
make test
make benchmark-basic
```

## Definition of done

```text
make up starts system
client can submit task
mock agent completes task
logs show task lifecycle
```

---

# Phase 6 — Event logging and metrics

## Goal

Make benchmarks possible.

## Tasks

```text
1. Create event logger.
2. Store events as JSONL.
3. Add traceId to every task.
4. Add timestamps to events.
5. Add script to compute latency metrics.
6. Export summary.csv.
```

## Definition of done

```text
events.jsonl is generated
summary.csv is generated
latency metrics are computed
```

---

# Phase 7 — Python SDK v0.1

## Goal

Make agent implementation easier.

## Tasks

```text
1. Create python-sdk/tg_sdk.
2. Wrap generated protobuf types.
3. Create Agent base class.
4. Implement registration helper.
5. Implement gRPC agent server helper.
6. Implement heartbeat helper placeholder.
7. Create EchoAgent example.
8. Create FailingAgent example.
```

## Definition of done

```text
Python agent can be written with base class
Python agent registers itself
Python agent executes task from orchestrator
```

---

# Phase 8 — BDI-like agent

## Goal

Demonstrate BDI-style internal reasoning through the common contract.

## Tasks

```text
1. Create agents/bdi-agent.
2. Define beliefs.
3. Define desires.
4. Define intentions.
5. Define simple plan library.
6. Map Task.goal to desire.
7. Select plan based on beliefs.
8. Return selectedPlan in metadata or BdiExtension.
9. Add route-planning example.
```

## Definition of done

```text
BDI agent receives task
BDI agent selects plan
BDI agent returns result
result includes selected plan or reasoning summary
```

---

# Phase 9 — Health and failure detection

## Goal

Detect unavailable agents.

## Tasks

```text
1. Add ReportHealth to registry.
2. Add heartbeat loop in SDK.
3. Add lastHeartbeatAt tracking.
4. Add failure detector loop.
5. Implement ALIVE -> SUSPECTED -> DEAD transitions.
6. Exclude DEAD agents from discovery.
7. Emit health events.
```

## Definition of done

```text
agent heartbeat is received
registry updates health
agent is marked DEAD after heartbeat stops
orchestrator does not assign tasks to DEAD agents
```

---

# Phase 10 — Retry and reassignment

## Goal

Recover from failed agents.

## Tasks

```text
1. Add execution timeout to orchestrator.
2. Add RetryPolicy support.
3. Increment task attempt.
4. Exclude failed agent on retry.
5. Rediscover compatible agents.
6. Reassign task.
7. Emit TASK_TIMEOUT and TASK_REASSIGNED.
8. Add failure benchmark.
```

## Definition of done

```text
task assigned to failing agent times out
task is reassigned to healthy agent
task completes after reassignment
recovery time is measurable
```

---

# Phase 11 — Messaging service

Status: concluída em 2026-10-03. Implementação e limitações em
`docs/implementation/phase-11b-messaging-service.md`.

## Goal

Support agent-to-agent communication.

## Tasks

```text
1. Add MessageEnvelope to active runtime flow.
2. Implement MessagingService.PublishMessage.
3. Implement MessagingService.StreamMessages or direct delivery.
4. Add SendMessage to SDK.
5. Add message event logging.
6. Create agent-to-agent scenario.
```

## Definition of done

```text
Agent A sends message to Agent B
Agent B receives message
MESSAGE_SENT and MESSAGE_RECEIVED are emitted
```

---

# Phase 12 — LLM helper agent

## Goal

Add LLM as an auxiliary agent, not as the central orchestrator.

## Tasks

```text
1. Create agents/llm-agent.
2. Implement task-decomposition capability.
3. Implement explanation capability.
4. Validate structured LLM output.
5. Add LlmExtension fields where useful.
6. Add natural-language task scenario.
```

## Definition of done

```text
LLM agent receives natural-language task
LLM agent returns structured capabilities or subtasks
orchestrator validates output
orchestrator assigns subtasks to compatible agents
```

---

# Phase 13 — Benchmark suite

Before implementing the benchmark suite, complete **Phase 12D — SDK agent
authoring and scenarios**, documented in
`docs/implementation/phase-12d-sdk-agent-authoring-and-scenarios.md`.
It promotes `BdiAgent` and `LlmAgent` to public SDK authoring APIs and defines
the one-file Python scenario plus scenario-specific Compose model. Benchmarks
must consume that API instead of duplicating gRPC coordination scripts.

Also complete **Phase 12E — runtime subtasks and workflows**, documented in
`docs/implementation/phase-12e-runtime-subtasks-and-workflows.md`. It adds the
deterministic workflow engine required for the client to submit one question
while the runtime plans, validates, schedules, correlates, and aggregates
subtasks.

## Goal

Run reproducible experiments.

## Tasks

```text
1. Implement Scenario A: basic execution.
2. Implement Scenario B: policy comparison.
3. Implement Scenario C: heterogeneous cooperation.
4. Implement Scenario D: failure and reassignment.
5. Implement Scenario E: LLM-assisted task.
6. Export metrics.
7. Generate charts.
```

## Definition of done

```text
all scenarios run from command line
results are saved
charts are generated
metrics are reproducible
```

---

# Phase 14 — Contract freeze v1.0

## Goal

Stabilize the final contract for the monograph.

## Tasks

```text
1. Review all fields used by implementation.
2. Remove unused experimental fields or mark as future work.
3. Freeze status lifecycle.
4. Freeze error codes.
5. Freeze event types.
6. Freeze service APIs.
7. Update documentation.
8. Tag release v1.0.0.
```

## Definition of done

```text
contract is stable
implementation uses frozen contract
benchmarks run on frozen version
documentation matches implementation
```

---

# Phase 15 — Final packaging

## Goal

Prepare repository for evaluation and presentation.

## Tasks

```text
1. Clean README.
2. Add quickstart.
3. Add architecture diagram.
4. Add benchmark instructions.ExecuteTask
5. Add demo script.
6. Add sample outputs.
7. Add limitations.
8. Add future work.
9. Prepare presentation material.
```

## Definition of done

```text
fresh clone can run demo
fresh clone can run benchmarks
repo explains architecture
repo explains contribution
```
