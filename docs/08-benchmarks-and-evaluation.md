# 08 — Benchmarks and Evaluation

## Purpose

The evaluation must show whether the proposed contract and runtime support cooperation among heterogeneous agents.

The benchmarks should not be excessive. They must be reproducible and directly connected to the research questions.

## Main evaluation questions

```text
1. Can heterogeneous agents cooperate using the same contract?
2. What is the overhead of using the runtime?
3. How long does discovery and assignment take?
4. How does the runtime behave when an agent fails?
5. What changes when LLM-assisted task decomposition is used?
```

## Core metrics

## Discovery latency

Time between task creation and agent selection.

```text
discoveryLatencyMs = AGENT_SELECTED.timestamp - TASK_CREATED.timestamp
```

## Queue latency

Time between task creation and task assignment.

```text
queueLatencyMs = TASK_ASSIGNED.timestamp - TASK_CREATED.timestamp
```

## Execution latency

Time between task start and task completion.

```text
executionLatencyMs = TASK_COMPLETED.timestamp - TASK_STARTED.timestamp
```

## Total latency

Time between task creation and completion.

```text
totalLatencyMs = TASK_COMPLETED.timestamp - TASK_CREATED.timestamp
```

## Failure detection time

Time between last heartbeat and DEAD status.

```text
failureDetectionMs = AGENT_DEAD.timestamp - lastHeartbeatAt
```

## Recovery time

Time between timeout/failure and reassignment.

```text
recoveryMs = TASK_REASSIGNED.timestamp - TASK_TIMEOUT.timestamp
```

## Message count

Number of MessageEnvelope objects exchanged during task execution.

## Reassignment count

Number of times a task is reassigned before terminal state.

## Success rate

```text
successRate = completedTasks / submittedTasks
```

---

# Benchmark scenarios

## Scenario A — Basic execution

Goal:

```text
prove that registry, orchestrator, and mock agent work end to end
```

Setup:

```text
1 registry
1 orchestrator
1 mock agent
1 client
```

Task:

```text
requiredCapabilities = ["echo"]
```

Measure:

```text
discovery latency
execution latency
total latency
```

Expected result:

```text
task completes successfully
all lifecycle events are emitted
```

---

## Scenario B — Multiple compatible agents

Goal:

```text
compare selection policies
```

Setup:

```text
1 registry
1 orchestrator
3 mock agents with same capability
```

Policies:

```text
FIRST_AVAILABLE
ROUND_ROBIN
LEAST_LOADED
```

Measure:

```text
task distribution per agent
average latency
p95 latency
load distribution
```

Expected result:

```text
FIRST_AVAILABLE concentrates tasks
ROUND_ROBIN distributes evenly
LEAST_LOADED follows reported runtime load
```

---

## Scenario C — Heterogeneous cooperation

Goal:

```text
show cooperation between BDI and LLM agents
```

Setup:

```text
1 LLM planner/explainer agent
1 BDI-like route planner agent
1 orchestrator
1 registry
```

Flow:

```text
1. Client submits natural-language task.
2. LLM agent suggests subtasks or capabilities.
3. BDI agent performs structured route planning.
4. LLM agent explains final result.
```

Measure:

```text
total latency
number of subtasks
number of messages
success rate
qualitative clarity of output
```

Expected result:

```text
runtime coordinates both agents using the same contract
```

---

## Scenario D — Failure and reassignment

Goal:

```text
show runtime recovery from agent failure
```

Setup:

```text
Agent A has capability route-planning but fails
Agent B has same capability and remains healthy
```

Flow:

```text
1. Task assigned to Agent A.
2. Agent A fails or times out.
3. Runtime detects failure.
4. Task is reassigned to Agent B.
5. Agent B completes task.
```

Measure:

```text
failure detection time
reassignment time
total latency with failure
total latency without failure
reassignment count
```

Expected result:

```text
task completes if retry policy allows reassignment
```

---

## Scenario E — LLM-assisted vs structured task

Goal:

```text
compare deterministic orchestration with LLM-assisted preprocessing
```

Case 1:

```text
task already has requiredCapabilities
```

Case 2:

```text
task is natural language and requires LLM capability inference
```

Measure:

```text
total latency
extra overhead from LLM call
success rate
quality of selected capabilities
```

Expected result:

```text
LLM-assisted mode is more flexible but slower and less deterministic
```

---

# Data collection

Every benchmark run should produce:

```text
events.jsonl
results.json
summary.csv
```

Suggested event format:

```json
{
  "eventId": "evt-001",
  "taskId": "task-001",
  "type": "TASK_ASSIGNED",
  "timestamp": "2026-05-16T12:00:00Z",
  "agentId": "agent-bdi-01",
  "trace": {
    "traceId": "trace-001"
  }
}
```

## Suggested benchmark folder

```text
benchmarks/
  scenarios/
    scenario_a_basic.py
    scenario_b_policies.py
    scenario_c_heterogeneous.py
    scenario_d_failure.py
    scenario_e_llm_assisted.py
  results/
    run-001/
      events.jsonl
      results.json
      summary.csv
  analysis/
    analyze_results.py
    plot_results.py
```

## Minimum final charts

```text
latency by scenario
latency by orchestration policy
failure recovery time
task distribution by agent
message count by scenario
```

## Threats to validity

Mention these in the TG:

```text
small number of agents
synthetic tasks
local Docker environment
LLM latency variance
mock BDI implementation instead of full Jason
simple failure detector
limited comparison with external frameworks
```
