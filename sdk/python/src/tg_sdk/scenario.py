import uuid

import grpc

from contract.v1 import contract_pb2, contract_pb2_grpc
from tg_sdk.models import TaskResult, mapping_to_struct


class ScenarioResult:
    def __init__(self, result):
        self.raw = result
        converted = TaskResult.from_proto(result)
        self.task_id = converted.task_id
        self.agent_id = converted.agent_id
        self.status = converted.status
        self.output = dict(converted.output)
        self.metadata = dict(converted.metadata)
        self.error = converted.error_message

    def assert_completed(self):
        if self.raw.status != contract_pb2.TASK_STATUS_COMPLETED:
            raise AssertionError(
                f"task {self.task_id} did not complete: {self.error or self.status}"
            )
        return self


class Scenario:
    """Cliente de cenário com trace compartilhado e valores Python.

    É o adaptador transitório enquanto o orchestrator ainda não executa
    workflows: cada ``submit`` continua passando pelo orchestrator.
    """

    def __init__(self, name, orchestrator_addr="localhost:50052"):
        self.name = name
        self.trace_id = str(uuid.uuid4())
        channel = grpc.insecure_channel(orchestrator_addr)
        self._channel = channel
        self._stub = contract_pb2_grpc.OrchestratorServiceStub(channel)
        self.results = {}

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
    ):
        task = contract_pb2.Task(
            task_id=str(uuid.uuid4()),
            type=task_type,
            goal=goal,
            payload=mapping_to_struct(payload),
            required_capabilities=list(capabilities),
            trace=contract_pb2.TraceContext(
                trace_id=self.trace_id,
                correlation_id=self.name,
            ),
        )
        if bdi_goal or intention_id:
            task.bdi.CopyFrom(
                contract_pb2.BdiExtension(
                    goal=bdi_goal or "",
                    intention_id=intention_id or str(uuid.uuid4()),
                )
            )

        response = self._stub.SubmitTask(
            contract_pb2.SubmitTaskRequest(task=task)
        )
        if response.HasField("error") and response.error.message:
            raise RuntimeError(f"{step}: {response.error.message}")

        result = ScenarioResult(response.result)
        self.results[step] = result
        return result

    def close(self):
        self._channel.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
