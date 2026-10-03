# 07 — Messaging and Failures

## Purpose

The runtime must allow agents to communicate and must recover when agents fail.

This document defines the minimum viable behavior for messaging, heartbeat, failure detection, and task reassignment.

---

# Messaging

## MessageEnvelope

All messages must use the MessageEnvelope contract.

Required fields:

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

Optional fields:

```text
replyTo
ttlMs
taskId
metadata
```

## Minimum message types

```text
REQUEST
RESPONSE
INFORM
ERROR
HEARTBEAT
```

## Optional message types

```text
PROPOSE
ACCEPT
REJECT
REFUSE
FAILURE
QUERY
CONFIRM
```

## Implementation phase 1

Do not implement a complex message broker first.

Start with:

```text
orchestrator-mediated messaging
in-memory routing
or simple direct gRPC SendMessage
```

## Implementation phase 2

Add a MessagingService:

```text
PublishMessage(MessageEnvelope) -> MessageAck
StreamMessages(StreamMessagesRequest) -> stream MessageEnvelope
```

This phase is implemented by `runtime/services/messaging`. The current broker
is in-memory, at-most-once, and supports one active stream per receiver. Durable
queues, redelivery, and multiple consumer groups remain future work.

## Message correlation

Use:

```text
conversationId — groups a dialogue
correlationId — links request and response
replyTo — references previous message
traceId — links message to task execution path
```

## Example

```json
{
  "messageId": "msg-001",
  "conversationId": "conv-001",
  "correlationId": "corr-001",
  "senderId": "agent-bdi-01",
  "receiverId": "agent-llm-01",
  "type": "REQUEST",
  "payload": {
    "question": "Explain this route decision"
  },
  "timestamp": "2026-05-16T12:00:00Z",
  "trace": {
    "traceId": "trace-001"
  }
}
```

---

# Heartbeat

## Purpose

Heartbeat tells the runtime that an agent is alive.

## Minimum heartbeat payload

```text
agentId
status
timestamp
lastHeartbeatAt
currentTaskCount
load
```

## Recommended interval

```text
2 seconds for demos
5 seconds for benchmarks
```

## Registry behavior

When heartbeat arrives:

```text
update lastHeartbeatAt
update status
update currentTaskCount
update load
```

---

# Failure detection

## Minimum policy

Use fixed timeouts.

Example:

```text
heartbeatInterval = 5s
suspectedTimeout = 10s
deadTimeout = 20s
```

Status transitions:

```text
ALIVE -> SUSPECTED -> DEAD
```

Rules:

```text
if now - lastHeartbeatAt > suspectedTimeout:
  status = SUSPECTED

if now - lastHeartbeatAt > deadTimeout:
  status = DEAD
```

## Why not adaptive detector first

Adaptive failure detectors are interesting, but they increase complexity.

Use them only as optional future work.

---

# Task reassignment

## When reassignment happens

Reassignment should happen when:

```text
assigned agent becomes DEAD
task execution times out
agent returns retryable error
connection to agent fails
```

## Reassignment algorithm

```text
1. Detect failure or timeout.
2. Emit TASK_TIMEOUT or TASK_FAILED.
3. Increment task attempt.
4. Check retry policy.
5. Exclude previously failed agent if needed.
6. Discover compatible agents again.
7. Assign task to new agent.
8. Emit TASK_REASSIGNED.
9. Continue execution.
```

## Retry policy

Minimum fields:

```text
maxAttempts
backoffMs
retryOn
```

Default:

```text
maxAttempts = 1
backoffMs = 0
```

For failure benchmark:

```text
maxAttempts = 2
retryOn = [TIMEOUT, AGENT_UNAVAILABLE, EXECUTION_FAILED]
```

---

# Failure benchmark scenario

## Setup

```text
Agent A: route-planning, configured to fail
Agent B: route-planning, healthy
Task requires: route-planning
```

## Expected flow

```text
1. Orchestrator assigns task to Agent A.
2. Agent A fails or stops heartbeat.
3. Failure detector marks Agent A as DEAD.
4. Orchestrator reassigns task to Agent B.
5. Agent B completes task.
6. Runtime emits all events.
```

## Metrics

```text
time to detect failure
time to reassign task
total latency with failure
total latency without failure
overhead caused by failure recovery
number of messages
number of attempts
```
