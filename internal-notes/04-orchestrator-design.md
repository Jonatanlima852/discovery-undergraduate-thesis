# 04 — Orchestrator Design

## Purpose

The orchestrator is responsible for operational coordination.

It receives tasks, selects agents, tracks task lifecycle, handles failures, and emits events.

It is not required to semantically understand every task like an LLM.

## What orchestration means in this project

Orchestration means:

```text
receive Task
validate Task
find compatible agents
select one agent
assign Task
monitor execution
handle timeout
retry or reassign when needed
record events
return TaskResult
```

## Why the orchestrator should not be only an LLM

A fully LLM-based orchestrator has problems:

```text
less deterministic
harder to benchmark
higher latency
higher cost
harder to reproduce experimentally
weaker failure guarantees
```

The runtime needs predictable behavior for:

```text
heartbeat timeout
agent status transition
task reassignment
retry limits
benchmark metrics
```

Therefore, the main orchestrator should be deterministic.

## Best use of LLMs

LLMs should be auxiliary agents.

They can help with:

```text
task decomposition
capability inference
natural-language interpretation
explanation generation
fallback reasoning
```

But the final operational control remains with the orchestrator.

## Recommended orchestration modes

## Mode 1 — Deterministic baseline

Policy:

```text
FIRST_AVAILABLE
```

Behavior:

```text
select the first alive agent that satisfies requiredCapabilities
```

Use this first to prove the full flow.

## Mode 2 — Load-aware deterministic policy

Policy:

```text
LOWEST_LOAD
```

Behavior:

```text
select the alive compatible agent with the lowest reported load
```

Use this to show that runtime state affects orchestration.

## Mode 3 — Capability score

Policy:

```text
CAPABILITY_SCORE
```

Behavior:

```text
score each candidate by how well its capabilities match the task
select highest score
```

Use this only after FIRST_AVAILABLE and LOWEST_LOAD work.

## Mode 4 — LLM-assisted orchestration

Behavior:

```text
if task.requiredCapabilities is empty or task is ambiguous:
  call LLM planner agent
  receive suggested capabilities or subtasks
  then use deterministic orchestration
```

This is the best hybrid mode for the TG.

## Core algorithm

```text
1. Receive task.
2. Validate required fields.
3. Emit TASK_CREATED.
4. If task is ambiguous, optionally call LLM planner agent.
5. Emit TASK_QUEUED.
6. Discover agents by requiredCapabilities.
7. Filter out DEAD and SUSPECTED agents.
8. Apply selection policy.
9. Emit AGENT_SELECTED.
10. Assign task to selected agent.
11. Emit TASK_ASSIGNED.
12. Wait for result with timeout.
13. If success, emit TASK_COMPLETED.
14. If timeout, emit TASK_TIMEOUT.
15. If retry is allowed, reassign and emit TASK_REASSIGNED.
16. If retry is exhausted, emit TASK_FAILED.
```

## Pseudocode

```ts
async function orchestrate(task: Task): Promise<TaskResult> {
  emit("TASK_CREATED", task);

  const normalizedTask = await maybeUseLlmPlanner(task);

  emit("TASK_QUEUED", normalizedTask);

  const candidates = await registry.discoverAgents({
    requiredCapabilities: normalizedTask.requiredCapabilities,
  });

  const aliveCandidates = candidates.filter(agent =>
    agent.status === "ALIVE" || agent.status === "BUSY"
  );

  if (aliveCandidates.length === 0) {
    return failTask(normalizedTask, "CAPABILITY_NOT_FOUND");
  }

  const selected = selectAgent(
    normalizedTask,
    aliveCandidates,
    normalizedTask.selectionPolicy?.strategy ?? "FIRST_AVAILABLE"
  );

  emit("AGENT_SELECTED", normalizedTask, selected);
  emit("TASK_ASSIGNED", normalizedTask, selected);

  try {
    const result = await executeWithTimeout(selected, normalizedTask);
    emit("TASK_COMPLETED", normalizedTask, selected);
    return result;
  } catch (error) {
    emit("TASK_TIMEOUT", normalizedTask, selected);

    if (canRetry(normalizedTask)) {
      const nextTask = incrementAttempt(normalizedTask);
      emit("TASK_REASSIGNED", nextTask);
      return orchestrate(nextTask);
    }

    emit("TASK_FAILED", normalizedTask, selected);
    return failTask(normalizedTask, "EXECUTION_FAILED");
  }
}
```

## Agent selection policies

## FIRST_AVAILABLE

```text
select first compatible alive agent
```

Pros:

```text
simple
fast
easy to debug
best baseline
```

Cons:

```text
no load balancing
can overload first agent
```

## ROUND_ROBIN

```text
cycle through compatible agents
```

Pros:

```text
simple distribution
better than FIRST_AVAILABLE for repeated tasks
```

Cons:

```text
ignores load
ignores capability quality
```

## LEAST_LOADED

```text
select compatible agent with smallest load, then current task count
```

Pros:

```text
uses runtime state
reasonable benchmark policy
```

Cons:

```text
depends on accurate load reporting
```

## CAPABILITY_SCORE

```text
select agent with highest capability match score
```

Pros:

```text
better semantic matching
useful when agents have overlapping capabilities
```

Cons:

```text
requires more careful capability modeling
```

## Recommended implementation order

```text
1. FIRST_AVAILABLE
2. LOWEST_LOAD
3. retry and reassignment
4. optional LLM planner
5. optional CAPABILITY_SCORE
```

## Important design rule

The LLM may suggest tasks or capabilities, but the runtime must validate them.

Never blindly trust LLM output.

Validation rules:

```text
each suggested subtask must have a goal
each suggested capability must be non-empty
task IDs must be generated by runtime, not LLM
retry policy must be controlled by runtime
agent selection must be validated against Registry
```
