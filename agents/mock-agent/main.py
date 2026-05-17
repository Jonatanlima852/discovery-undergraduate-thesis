import logging
import os
import random
import sys
import time
import uuid
from concurrent import futures

import grpc
from google.protobuf import timestamp_pb2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../sdk/python/src"))

from contract.v1 import contract_pb2, contract_pb2_grpc

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [mock-agent] %(message)s",
)
log = logging.getLogger(__name__)


def _now():
    ts = timestamp_pb2.Timestamp()
    ts.GetCurrentTime()
    return ts


def _build_descriptor(agent_id, capability, port):
    return contract_pb2.AgentDescriptor(
        agent_id=agent_id,
        name=f"Mock Agent ({agent_id})",
        runtime="python-mock",
        contract_version="0.1.0",
        capabilities=[
            contract_pb2.Capability(
                capability_id=capability,
                name=capability,
                description=f"Mock capability: {capability}",
            )
        ],
        endpoint=contract_pb2.AgentEndpoint(
            protocol="grpc",
            address=f"localhost:{port}",
        ),
        status=contract_pb2.AGENT_STATUS_ALIVE,
    )


class MockAgentServicer(contract_pb2_grpc.AgentServiceServicer):
    def __init__(self, agent_id, delay_ms, fail_rate):
        self.agent_id = agent_id
        self.delay_ms = delay_ms
        self.fail_rate = fail_rate

    def ExecuteTask(self, request, context):
        task = request.task
        log.info("task received task_id=%s goal=%s", task.task_id, task.goal)

        time.sleep(self.delay_ms / 1000)

        if random.random() < self.fail_rate:
            log.warning("task failed (intentional) task_id=%s", task.task_id)
            result = contract_pb2.TaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status=contract_pb2.TASK_STATUS_FAILED,
                completed_at=_now(),
                trace=task.trace,
                error=contract_pb2.ErrorInfo(
                    code=contract_pb2.ERROR_CODE_EXECUTION_FAILED,
                    message="intentional failure (fail_rate)",
                    retryable=True,
                ),
            )
        else:
            log.info("task completed task_id=%s", task.task_id)
            result = contract_pb2.TaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status=contract_pb2.TASK_STATUS_COMPLETED,
                completed_at=_now(),
                trace=task.trace,
            )

        return contract_pb2.ExecuteTaskResponse(result=result)


def register(registry_addr, descriptor):
    channel = grpc.insecure_channel(registry_addr)
    stub = contract_pb2_grpc.RegistryServiceStub(channel)
    resp = stub.RegisterAgent(
        contract_pb2.RegisterAgentRequest(agent=descriptor)
    )
    if resp.success:
        log.info("registered with registry addr=%s", registry_addr)
    else:
        log.error("registration failed: %s", resp.message)
        sys.exit(1)


def main():
    agent_id = os.getenv("AGENT_ID", "mock-agent-01")
    port = int(os.getenv("AGENT_PORT", "60051"))
    registry_addr = os.getenv("REGISTRY_ADDR", "localhost:50051")
    capability = os.getenv("CAPABILITY", "echo")
    delay_ms = int(os.getenv("DELAY_MS", "100"))
    fail_rate = float(os.getenv("FAIL_RATE", "0.0"))

    descriptor = _build_descriptor(agent_id, capability, port)
    register(registry_addr, descriptor)

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    contract_pb2_grpc.add_AgentServiceServicer_to_server(
        MockAgentServicer(agent_id, delay_ms, fail_rate), server
    )
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    log.info("agent service started agent_id=%s port=%d", agent_id, port)
    server.wait_for_termination()


if __name__ == "__main__":
    main()
