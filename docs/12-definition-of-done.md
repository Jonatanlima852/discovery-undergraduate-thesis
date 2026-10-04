# 12 — Definition of Done

## Purpose

This document defines completion criteria for each part of the implementation.

Use it to avoid vague progress.

---

# Contract is done when

```text
contract.proto compiles
Go code is generated
Python code is generated
all core entities exist
all core services exist
contract version is declared
README explains the contract
```

Core entities:

```text
AgentDescriptor
Capability
Task
TaskResult
TaskEvent
MessageEnvelope
HealthStatus
ErrorInfo
TraceContext
```

Core services:

```text
RegistryService
OrchestratorService
AgentService
```

---

# Registry is done when

```text
agent can register
agent can unregister
agent can be fetched by ID
agents can be discovered by capability
agent status is stored
health reports update status
unit tests cover successful and failed registration
```

---

# Mock agent is done when

```text
agent starts locally
agent registers with registry
agent exposes ExecuteTask
agent returns TaskResult
agent can simulate delay
agent can simulate failure
```

---

# Orchestrator v0.1 is done when

```text
client submits Task
orchestrator validates Task
orchestrator emits TASK_CREATED
orchestrator discovers compatible agents
orchestrator selects agent using FIRST_AVAILABLE
orchestrator sends Task to agent
orchestrator receives TaskResult
orchestrator emits TASK_COMPLETED
orchestrator returns result to client
```

---

# Docker baseline is done when

```text
make up starts registry, orchestrator, and mock agent
client can submit task using docker-compose network
logs show registration and task lifecycle
make down stops all services
```

---

# Event logging is done when

```text
events are written to JSONL
all events include taskId and traceId
events include timestamps
benchmark script reads events
summary.csv is generated
```

---

# Python SDK is done when

```text
Agent base class exists
agent can register automatically
agent can expose ExecuteTask
agent can send heartbeat
agent can return TaskResult
agent maps exceptions to ErrorInfo
example EchoAgent works
example FailingAgent works
```

---

# BDI agent is done when

```text
BDI agent has beliefs
BDI agent maps Task.goal to desire
BDI agent selects a plan
BDI agent commits to an intention
BDI agent executes plan
BDI agent returns TaskResult
result includes selected plan or BDI metadata
```

---

# Failure detection is done when

```text
agents send heartbeat
registry stores lastHeartbeatAt
failure detector marks missing agent as SUSPECTED
failure detector marks missing agent as DEAD
orchestrator excludes DEAD agents from selection
```

---

# Reassignment is done when

```text
orchestrator detects timeout or unavailable agent
orchestrator increments attempt
orchestrator discovers another compatible agent
orchestrator emits TASK_REASSIGNED
new agent completes task
benchmark records recovery time
```

---

# Messaging is done when

```text
MessageEnvelope is used
Agent A can send message to Agent B
Agent B receives message
MESSAGE_SENT is emitted
MESSAGE_RECEIVED is emitted
conversationId and correlationId are preserved
```

---

# LLM agent is done when

```text
LLM agent is registered as normal agent
LLM agent exposes task-decomposition capability
LLM output is validated
orchestrator can use LLM output to create subtasks or infer capabilities
LLM agent can generate final explanation
```

---

# Benchmarks are done when

```text
Scenario A runs
Scenario B runs
Scenario C runs
Scenario D runs
Scenario E runs
results are saved
charts are generated
metrics are documented
```

Minimum scenarios:

```text
A: basic execution
B: selection policy comparison
C: heterogeneous BDI + LLM cooperation
D: failure and reassignment
E: LLM-assisted vs structured task
```

---

# Final repository is done when

Estado do contrato: `contract.v1` foi congelado como `1.0.0`; integridade é
verificada por `make contract-check`.

```text
fresh clone can run demo
fresh clone can run benchmarks
README has quickstart
docs explain architecture
contract is frozen
limitations are documented
future work is documented
```
