import json
import tempfile
import unittest
from pathlib import Path

from contract.v1 import contract_pb2
from tg_sdk import Scenario, TaskResult


def response(*, task_id, agent_id, metadata=None, output=None):
    result = TaskResult(
        task_id=task_id,
        agent_id=agent_id,
        status="TASK_STATUS_COMPLETED",
        metadata=metadata or {},
        output=output or {},
        trace={"trace_id": "replaced-by-request"},
    ).to_proto()
    return contract_pb2.SubmitTaskResponse(result=result)


class FakeOrchestrator:
    def __init__(self, replies):
        self.replies = list(replies)
        self.requests = []

    def SubmitTask(self, request):
        self.requests.append(request)
        reply = self.replies.pop(0)
        reply.result.task_id = request.task.task_id
        reply.result.trace.CopyFrom(request.task.trace)
        return reply


class ScenarioTests(unittest.TestCase):
    def test_run_submits_declared_entry_and_returns_report(self):
        stub = FakeOrchestrator([
            response(
                task_id="ignored",
                agent_id="llm-1",
                metadata={"provider": "openai"},
                output={"answer": "ok"},
            )
        ])
        scenario = Scenario(
            "single-entry",
            entry_capability="task-decomposition",
            orchestrator_stub=stub,
        )

        report = scenario.run("Planeje uma rota")

        report.assert_completed().assert_agent_used("llm-1")
        report.assert_agent_kind_used("llm")
        self.assertEqual(report.output, {"answer": "ok"})
        self.assertEqual(
            list(stub.requests[0].task.required_capabilities),
            ["task-decomposition"],
        )
        self.assertEqual(stub.requests[0].task.trace.trace_id, scenario.trace_id)

    def test_report_asserts_multiple_agent_kinds_and_saves_json(self):
        stub = FakeOrchestrator([
            response(
                task_id="one", agent_id="llm-1",
                metadata={"provider": "openai"},
            ),
            response(
                task_id="two", agent_id="bdi-1",
                metadata={"selected_plan": "via_b"},
            ),
        ])
        scenario = Scenario("heterogeneous", orchestrator_stub=stub)
        scenario.submit("decompose", goal="goal", capabilities=["decompose"])
        scenario.submit("route", goal="route", capabilities=["route"])

        report = scenario.report()
        report.assert_completed()
        report.assert_agent_kind_used("llm").assert_agent_kind_used("bdi")
        self.assertEqual(len(report.events), 4)
        self.assertTrue(all(
            event["trace_id"] == scenario.trace_id for event in report.events
        ))

        with tempfile.TemporaryDirectory() as directory:
            path = report.save(Path(directory) / "report.json")
            saved = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(saved["status"], "COMPLETED")
        self.assertEqual(saved["trace_id"], scenario.trace_id)
        self.assertEqual(set(saved["results"]), {"decompose", "route"})

    def test_submit_forwards_timeout_and_retry_policy(self):
        stub = FakeOrchestrator([
            response(task_id="one", agent_id="healthy")
        ])
        scenario = Scenario("retry", orchestrator_stub=stub)

        scenario.submit(
            "recover",
            goal="test",
            capabilities=["echo"],
            deadline_ms=50,
            max_attempts=3,
            backoff_ms=10,
            exclude_failed_agent=True,
        )

        task = stub.requests[0].task
        self.assertEqual(task.deadline_ms, 50)
        self.assertEqual(task.retry_policy.max_attempts, 3)
        self.assertEqual(task.retry_policy.backoff_ms, 10)
        self.assertTrue(task.retry_policy.exclude_failed_agent)

    def test_run_requires_entry_capability(self):
        scenario = Scenario("invalid", orchestrator_stub=FakeOrchestrator([]))

        with self.assertRaisesRegex(ValueError, "entry_capability"):
            scenario.run("goal")


if __name__ == "__main__":
    unittest.main()
