# 11 — Decisions and Trade-offs

## Purpose

This document records the design decisions of the project.

These decisions should be referenced during implementation and in the monograph.

---

# Decision 1 — Deterministic runtime orchestration

## Decision

The orchestrator is deterministic by default.

It uses explicit policies such as:

```text
FIRST_AVAILABLE
ROUND_ROBIN
LOWEST_LOAD
CAPABILITY_SCORE
```

## Reason

Deterministic orchestration is:

```text
easier to benchmark
easier to debug
more reproducible
better for failure handling
more appropriate for lifecycle control
```

## Trade-off

It is less semantically flexible than an LLM-based orchestrator.

## Mitigation

Use LLM agents as auxiliary planners, explainers, and capability inferencers.

---

# Decision 2 — LLM as auxiliary agent

## Decision

The LLM is not the central orchestrator.

It is represented as a normal agent with capabilities.

Examples:

```text
task-decomposition
capability-inference
explanation
summarization
```

## Reason

This preserves the main contribution of the runtime.

The runtime coordinates heterogeneous agents. The LLM participates in the system, but does not replace the system.

## Trade-off

Some highly semantic planning is delegated indirectly, not built into the orchestrator itself.

---

# Decision 3 — Simplified BDI agent before Jason integration

## Decision

Implement a BDI-like Python agent before attempting integration with Jason or AgentSpeak.

## Reason

This reduces risk and keeps the TG implementable.

A simplified BDI model is enough to demonstrate:

```text
beliefs
goals/desires
intentions
plan selection
task execution
```

## Trade-off

The first BDI implementation is not a full formal BDI interpreter.

## Mitigation

Mention Jason integration as future work or optional extension.

---

# Decision 4 — gRPC and Protocol Buffers

## Decision

Use gRPC and Protocol Buffers for runtime service communication.

## Reason

They provide:

```text
explicit service contracts
typed messages
code generation
language interoperability
streaming support
schema evolution
```

## Trade-off

They add setup complexity compared with plain HTTP/JSON.

## Mitigation

Use generated code and keep services small.

---

# Decision 5 — JSON-like payloads inside typed envelope

## Decision

Use typed envelopes with flexible payloads.

Example:

```text
Task has typed metadata, lifecycle, trace, and requiredCapabilities.
Task.payload is flexible JSON/Struct.
```

## Reason

This balances structure and flexibility.

The runtime needs typed operational fields, while agents need domain-specific payloads.

## Trade-off

Payload validation becomes partly application-specific.

## Mitigation

Use inputSchema/outputSchema in Capability when needed.

---

# Decision 6 — Fixed timeout failure detector first

## Decision

Use fixed heartbeat timeouts for initial failure detection.

## Reason

It is simple, clear, and easy to evaluate.

## Trade-off

It may produce false positives or slow detection under variable latency.

## Mitigation

Mention adaptive failure detection as future work.

---

# Decision 7 — Event-based benchmark extraction

## Decision

All benchmark metrics should be derived from TaskEvent logs.

## Reason

This keeps evaluation reproducible.

Metrics can be calculated from:

```text
TASK_CREATED
TASK_ASSIGNED
TASK_STARTED
TASK_COMPLETED
TASK_TIMEOUT
TASK_REASSIGNED
```

## Trade-off

Requires careful event emission.

## Mitigation

Make event emission part of the orchestrator's core behavior.

---

# Decision 8 — In-memory first, persistence later

## Decision

Start with in-memory state and JSONL event logs.

## Reason

The project evaluates concepts and runtime behavior, not database engineering.

## Trade-off

State is lost on service restart.

## Mitigation

Use this as an explicit limitation.

---

# Decision 9 — Minimal FIPA-inspired messaging

## Decision

Use a reduced set of message types inspired by FIPA ACL, but do not implement full FIPA semantics.

## Reason

Full FIPA compliance would expand the project too much.

## Trade-off

Less formal communicative semantics.

## Mitigation

Define clear MessageEnvelope fields and basic performatives.

## Implemented scope

The runtime uses an in-memory gRPC `MessagingService` with publish and
server-streaming receive operations. Delivery is at-most-once and state is not
durable across restarts. This is sufficient for correlated agent-to-agent
communication while keeping external brokers and full FIPA semantics outside
the evaluated scope.

---

# Decision 10 — Contract evolves, but core stays stable

## Decision

The contract may evolve, but core entities should remain stable.

Core:

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

## Reason

The project needs extensibility but also needs a stable contribution.

## Trade-off

Some early design choices may need adaptation.

## Mitigation

Use optional fields, versioning, and extension objects.
