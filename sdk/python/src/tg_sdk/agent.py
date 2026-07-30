import logging
import os
import threading
from concurrent import futures

import grpc
from google.protobuf import timestamp_pb2

from contract.v1 import contract_pb2, contract_pb2_grpc

log = logging.getLogger(__name__)


class _AgentServicer(contract_pb2_grpc.AgentServiceServicer):
    """Adapta o AgentService gRPC para o método execute_task do Agent."""

    def __init__(self, agent):
        self._agent = agent

    def ExecuteTask(self, request, context):
        self._agent._task_started()
        try:
            result = self._agent.execute_task(request.task)
            return contract_pb2.ExecuteTaskResponse(result=result)
        finally:
            self._agent._task_finished()


class Agent:
    """Classe base para agentes do TG Runtime.

    Cuida do registro no Registry e do servidor gRPC do AgentService.
    Subclasses implementam apenas execute_task com a lógica de negócio.
    """

    def __init__(self, agent_id, name, capabilities, host, port, registry_addr,
                 runtime="python-sdk", contract_version="0.1.0",
                 heartbeat_interval_seconds=None):
        self.agent_id = agent_id
        self.name = name
        self.capabilities = capabilities
        self.host = host
        self.port = port
        self.registry_addr = registry_addr
        self.runtime = runtime
        self.contract_version = contract_version
        if heartbeat_interval_seconds is None:
            heartbeat_interval_seconds = float(
                os.getenv("HEARTBEAT_INTERVAL_SECONDS", "5")
            )
        if heartbeat_interval_seconds <= 0:
            raise ValueError("heartbeat_interval_seconds deve ser maior que zero")
        self.heartbeat_interval_seconds = heartbeat_interval_seconds
        self._current_task_count = 0
        self._task_count_lock = threading.Lock()
        self._heartbeat_stop = threading.Event()
        self._heartbeat_thread = None

    def execute_task(self, task):
        """Recebe um contract_pb2.Task e devolve um contract_pb2.TaskResult.

        Subclasses devem sobrescrever este método com a lógica do agente.
        """
        raise NotImplementedError("subclasses devem implementar execute_task")

    def build_descriptor(self):
        return contract_pb2.AgentDescriptor(
            agent_id=self.agent_id,
            name=self.name,
            runtime=self.runtime,
            contract_version=self.contract_version,
            capabilities=[
                contract_pb2.Capability(
                    capability_id=capability_id,
                    name=capability_id,
                )
                for capability_id in self.capabilities
            ],
            endpoint=contract_pb2.AgentEndpoint(
                protocol="grpc",
                address=f"{self.host}:{self.port}",
            ),
            status=contract_pb2.AGENT_STATUS_ALIVE,
        )

    def register(self):
        channel = grpc.insecure_channel(self.registry_addr)
        stub = contract_pb2_grpc.RegistryServiceStub(channel)
        resp = stub.RegisterAgent(
            contract_pb2.RegisterAgentRequest(agent=self.build_descriptor())
        )
        if not resp.success:
            raise RuntimeError(f"registration failed: {resp.message}")
        log.info("agent_id=%s registered with registry addr=%s", self.agent_id, self.registry_addr)

    def _task_started(self):
        with self._task_count_lock:
            self._current_task_count += 1

    def _task_finished(self):
        with self._task_count_lock:
            self._current_task_count -= 1

    def _task_count(self):
        with self._task_count_lock:
            return self._current_task_count

    def heartbeat(self, stub):
        """Envia um único sinal de saúde ao Registry."""
        now = timestamp_pb2.Timestamp()
        now.GetCurrentTime()
        task_count = self._task_count()
        response = stub.ReportHealth(
            contract_pb2.ReportHealthRequest(
                health=contract_pb2.HealthStatus(
                    agent_id=self.agent_id,
                    status=contract_pb2.AGENT_STATUS_ALIVE,
                    timestamp=now,
                    last_heartbeat_at=now,
                    current_task_count=task_count,
                    load=1.0 if task_count else 0.0,
                )
            )
        )
        if not response.success:
            raise RuntimeError("heartbeat rejected by registry")

    def _heartbeat_loop(self):
        channel = grpc.insecure_channel(self.registry_addr)
        stub = contract_pb2_grpc.RegistryServiceStub(channel)
        try:
            while not self._heartbeat_stop.is_set():
                try:
                    self.heartbeat(stub)
                    log.debug("agent_id=%s heartbeat sent", self.agent_id)
                except grpc.RpcError as error:
                    log.warning(
                        "agent_id=%s heartbeat failed code=%s details=%s",
                        self.agent_id,
                        error.code(),
                        error.details(),
                    )
                except Exception:
                    log.exception("agent_id=%s heartbeat failed", self.agent_id)
                self._heartbeat_stop.wait(self.heartbeat_interval_seconds)
        finally:
            channel.close()

    def start_heartbeat(self):
        if self._heartbeat_thread is not None and self._heartbeat_thread.is_alive():
            return
        self._heartbeat_stop.clear()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            name=f"heartbeat-{self.agent_id}",
            daemon=True,
        )
        self._heartbeat_thread.start()
        log.info(
            "agent_id=%s heartbeat started interval_seconds=%s",
            self.agent_id,
            self.heartbeat_interval_seconds,
        )

    def stop_heartbeat(self):
        self._heartbeat_stop.set()
        if self._heartbeat_thread is not None:
            self._heartbeat_thread.join(timeout=self.heartbeat_interval_seconds + 1)
        self._heartbeat_thread = None

    def serve(self):
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
        contract_pb2_grpc.add_AgentServiceServicer_to_server(_AgentServicer(self), server)
        server.add_insecure_port(f"[::]:{self.port}")
        server.start()
        log.info("agent_id=%s service started port=%d", self.agent_id, self.port)
        server.wait_for_termination()

    def run(self):
        self.register()
        self.start_heartbeat()
        try:
            self.serve()
        finally:
            self.stop_heartbeat()
