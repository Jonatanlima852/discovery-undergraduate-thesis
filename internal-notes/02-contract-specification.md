# 02 — Contract Specification

## Purpose

The contract defines the common language used by agents and runtime services.

It must be minimal enough to implement during the TG, but expressive enough to support:

```text
agent discovery
task execution
message exchange
health monitoring
failure handling
benchmarking
BDI extensions
LLM extensions
```

## Versioning

Every agent must declare the contract version it supports.

Example:

```json
{
  "contractVersion": "1.0.0"
}
```

Recommended versioning strategy:

```text
0.1.0 — initial experimental contract (historical)
0.2.0 — planned intermediate version (historical)
1.0.0 — frozen TG evaluation contract (current)
```

Rules:

```text
1. New fields should be optional.
2. Existing field semantics should not be changed casually.
3. Breaking changes require a major version.
4. The runtime should reject unsupported major versions.
5. The checksum in `proto/contract/v1/contract.sha256` must match.
```

## Core entities

The minimum contract contains:

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

---

# AgentDescriptor

Represents an agent registered in the runtime.

## Required fields

```text
agentId
name
runtime
contractVersion
capabilities
endpoint
status
```

## Optional fields

```text
createdAt
updatedAt
metadata
```

## Example

```json
{
  "agentId": "agent-bdi-01",
  "name": "BDI Planner Agent",
  "runtime": "python-sdk",
  "contractVersion": "1.0.0",
  "capabilities": [
    {
      "capabilityId": "route-planning",
      "name": "route-planning",
      "description": "Computes a route based on constraints"
    }
  ],
  "endpoint": {
    "protocol": "grpc",
    "address": "bdi-agent:50051"
  },
  "status": "ALIVE"
}
```

---

# Capability

Represents something an agent can do.

## Required fields

```text
capabilityId
name
description
```

## Optional fields

```text
inputSchema
outputSchema
tags
costHint
latencyHintMs
metadata
currentTaskCount
load
```

## Design note

Do not start with formal ontologies. Use simple capability names, descriptions, and tags first.

Example:

```json
{
  "capabilityId": "task-decomposition",
  "name": "task-decomposition",
  "description": "Breaks a high-level task into executable subtasks",
  "tags": ["llm", "planning"]
}
```

---

# Task

Represents a unit of work.

## Required fields

```text
taskId
type
goal
payload
requiredCapabilities
status
trace
createdAt
```

## Optional fields

```text
priority
deadlineMs
parentTaskId
assignedAgentId
attempt
retryPolicy
selectionPolicy
bdi
llm
metadata
```

## Example

```json
{
  "taskId": "task-001",
  "type": "PLAN_ROUTE",
  "goal": "Find a valid route from A to B",
  "payload": {
    "origin": "A",
    "destination": "B"
  },
  "requiredCapabilities": ["route-planning"],
  "status": "CREATED",
  "trace": {
    "traceId": "trace-001"
  },
  "createdAt": "2026-05-16T12:00:00Z"
}
```

---

# Task lifecycle

Minimum lifecycle:

```text
CREATED
  -> QUEUED
  -> ASSIGNED
  -> RUNNING
  -> COMPLETED
```

Failure lifecycle:

```text
RUNNING
  -> TIMEOUT
  -> REASSIGNED
  -> RUNNING
  -> COMPLETED
```

Terminal failure:

```text
RUNNING
  -> FAILED
```

Supported statuses:

```text
CREATED
QUEUED
ASSIGNED
RUNNING
WAITING
COMPLETED
FAILED
CANCELLED
REASSIGNED
TIMEOUT
```

---

# TaskResult

Represents the outcome of a task.

## Required fields

```text
taskId
agentId
status
completedAt
trace
```

## Optional fields

```text
output
error
startedAt
metrics
metadata
```

## Example

```json
{
  "taskId": "task-001",
  "agentId": "agent-bdi-01",
  "status": "COMPLETED",
  "output": {
    "route": "A -> D -> B"
  },
  "completedAt": "2026-05-16T12:00:03Z",
  "trace": {
    "traceId": "trace-001"
  }
}
```

---

# TaskEvent

Represents an event in the task lifecycle.

Events are essential for benchmarking.

## Required fields

```text
eventId
taskId
type
timestamp
trace
```

## Optional fields

```text
agentId
details
```

## Event types

```text
TASK_CREATED
TASK_QUEUED
TASK_ASSIGNED
TASK_STARTED
TASK_COMPLETED
TASK_FAILED
TASK_TIMEOUT
TASK_REASSIGNED
AGENT_SELECTED
MESSAGE_SENT
MESSAGE_RECEIVED
```

## Metrics derived from events

```text
discovery latency = TASK_ASSIGNED - TASK_CREATED
execution latency = TASK_COMPLETED - TASK_STARTED
recovery time = TASK_REASSIGNED - TASK_TIMEOUT
total latency = TASK_COMPLETED - TASK_CREATED
```

---

# MessageEnvelope

Represents communication between agents.

## Required fields

```text
messageId
conversationId
correlationId
senderId
receiverId
type
payload
timestamp
trace
```

## Optional fields

```text
replyTo
ttlMs
taskId
metadata
```

## Message types

Minimum:

```text
REQUEST
RESPONSE
INFORM
ERROR
HEARTBEAT
```

Optional FIPA-inspired types:

```text
PROPOSE
ACCEPT
REJECT
REFUSE
FAILURE
QUERY
CONFIRM
```

---

# HealthStatus

Represents the operational status of an agent.

## Required fields

```text
agentId
status
timestamp
```

## Optional fields

```text
lastHeartbeatAt
currentTaskCount
load
details
```

## Status values

```text
UNKNOWN
ALIVE
BUSY
SUSPECTED
DEAD
DRAINING
```

---

# ErrorInfo

Represents standardized errors.

## Required fields

```text
code
message
retryable
```

## Optional fields

```text
details
```

## Error codes

```text
UNKNOWN
INVALID_TASK
CAPABILITY_NOT_FOUND
AGENT_UNAVAILABLE
TIMEOUT
EXECUTION_FAILED
CONTRACT_VERSION_UNSUPPORTED
MESSAGE_DELIVERY_FAILED
```

---

# TraceContext

Represents correlation and observability data.

## Required fields

```text
traceId
```

## Optional fields

```text
spanId
parentSpanId
correlationId
```

Trace context is required because the TG evaluation depends on latency, overhead, reassignment, and message count.

---

# BDI extension

Optional extension for BDI agents.

## Fields

```text
goal
beliefs
desires
intentions
selectedPlan
planLibraryRef
reasoningSummary
metadata
```

## Recommendation

Start with:

```text
goal
beliefs
selectedPlan
intentionId
```

Avoid implementing a full AgentSpeak model in the contract.

---

# LLM extension

Optional extension for LLM-based agents.

## Fields

```text
provider
model
prompt
systemInstruction
temperature
maxTokens
toolPolicy
confidence
explanation
reasoningSummary
metadata
```

## Recommendation

Do not include full chain-of-thought in the contract. Use explanation or reasoningSummary only.
