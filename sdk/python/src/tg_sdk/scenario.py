"""API pública para executar, correlacionar e verificar cenários."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import grpc

from contract.v1 import contract_pb2, contract_pb2_grpc
from tg_sdk.models import TaskResult, mapping_to_struct


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


class ScenarioResult:
    def __init__(self, result):
        self.raw = result
        self.value = TaskResult.from_proto(result)
        self.task_id = self.value.task_id
        self.agent_id = self.value.agent_id
        self.status = self.value.status
        self.output = dict(self.value.output)
        self.metadata = dict(self.value.metadata)
        self.error = self.value.error_message

    @property
    def agent_kind(self):
        if self.metadata.get("agent_kind"):
            return str(self.metadata["agent_kind"]).lower()
        if self.metadata.get("provider"):
            return "llm"
        if self.metadata.get("selected_plan"):
            return "bdi"
        return "generic"

    def assert_completed(self):
        if self.raw.status != contract_pb2.TASK_STATUS_COMPLETED:
            raise AssertionError(
                f"task {self.task_id} did not complete: {self.error or self.status}"
            )
        return self

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "agent_kind": self.agent_kind,
            "status": self.status,
            "output": self.output,
            "metadata": self.metadata,
            "error": self.error,
        }


@dataclass
class ScenarioReport:
    name: str
    trace_id: str
    results: Mapping[str, ScenarioResult]
    events: list[dict[str, Any]]

    @property
    def final_result(self):
        return next(reversed(self.results.values()), None)

    @property
    def output(self):
        return self.final_result.output if self.final_result else {}

    def assert_completed(self):
        if not self.results:
            raise AssertionError("scenario did not execute any step")
        for step, result in self.results.items():
            try:
                result.assert_completed()
            except AssertionError as error:
                raise AssertionError(f"step {step}: {error}") from error
        return self

    def assert_agent_used(self, agent_id):
        if not any(result.agent_id == agent_id for result in self.results.values()):
            raise AssertionError(f"agent was not used: {agent_id}")
        return self

    def assert_agent_kind_used(self, kind):
        normalized = kind.lower()
        if not any(result.agent_kind == normalized for result in self.results.values()):
            raise AssertionError(f"agent kind was not used: {kind}")
        return self

    def to_dict(self):
        statuses = [result.status for result in self.results.values()]
        status = (
            "COMPLETED"
            if statuses and all(value == "TASK_STATUS_COMPLETED" for value in statuses)
            else "FAILED"
        )
        return {
            "scenario": self.name,
            "trace_id": self.trace_id,
            "status": status,
            "results": {
                step: result.to_dict() for step, result in self.results.items()
            },
            "events": list(self.events),
        }

    def save(self, path):
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return destination


class Scenario:
    """Cliente de cenário com trace compartilhado e valores Python.

    ``submit`` é o adaptador transitório para múltiplas etapas enquanto o
    orchestrator ainda não executa workflows. ``run`` envia uma única entrada.
    """

    def __init__(
        self,
        name,
        orchestrator_addr="localhost:50052",
        *,
        agents=None,
        entry_capability=None,
        orchestrator_stub=None,
    ):
        self.name = name
        self.agents = tuple(agents or ())
        self.entry_capability = entry_capability
        self.trace_id = str(uuid.uuid4())
        self._channel = None
        if orchestrator_stub is None:
            self._channel = grpc.insecure_channel(orchestrator_addr)
            orchestrator_stub = contract_pb2_grpc.OrchestratorServiceStub(
                self._channel
            )
        self._stub = orchestrator_stub
        self.results = {}
        self.events = []

    def _event(self, event_type, step, **details):
        self.events.append({
            "type": event_type,
            "scenario": self.name,
            "step": step,
            "trace_id": self.trace_id,
            "timestamp": _utc_now(),
            **details,
        })

    def submit(
        self,
        step,
        *,
        goal,
        capabilities,
        task_type="SCENARIO_STEP",
        payload=None,
        bdi_goal=None,
        intention_id=None,
        deadline_ms=0,
        max_attempts=1,
        backoff_ms=0,
        exclude_failed_agent=False,
    ):
        task = contract_pb2.Task(
            task_id=str(uuid.uuid4()),
            type=task_type,
            goal=goal,
            payload=mapping_to_struct(payload),
            required_capabilities=list(capabilities),
            deadline_ms=deadline_ms,
            retry_policy=contract_pb2.RetryPolicy(
                max_attempts=max_attempts,
                backoff_ms=backoff_ms,
                exclude_failed_agent=exclude_failed_agent,
            ),
            trace=contract_pb2.TraceContext(
                trace_id=self.trace_id,
                correlation_id=self.name,
            ),
        )
        if bdi_goal or intention_id:
            task.bdi.CopyFrom(contract_pb2.BdiExtension(
                goal=bdi_goal or "",
                intention_id=intention_id or str(uuid.uuid4()),
            ))

        self._event("STEP_SUBMITTED", step, task_id=task.task_id)
        response = self._stub.SubmitTask(contract_pb2.SubmitTaskRequest(task=task))
        if response.HasField("error") and response.error.message:
            self._event(
                "STEP_REJECTED", step, task_id=task.task_id,
                error=response.error.message,
            )
            raise RuntimeError(f"{step}: {response.error.message}")

        result = ScenarioResult(response.result)
        self.results[step] = result
        self._event(
            "STEP_FINISHED", step, task_id=result.task_id,
            agent_id=result.agent_id, status=result.status,
        )
        return result

    def run(self, goal, *, payload=None, task_type="NATURAL_LANGUAGE"):
        if not self.entry_capability:
            raise ValueError("Scenario.run requires entry_capability")
        self.submit(
            "entry", goal=goal, capabilities=[self.entry_capability],
            task_type=task_type, payload=payload,
        )
        return self.report()

    ask = run

    def report(self):
        return ScenarioReport(
            name=self.name,
            trace_id=self.trace_id,
            results=dict(self.results),
            events=list(self.events),
        )

    def close(self):
        if self._channel is not None:
            self._channel.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
