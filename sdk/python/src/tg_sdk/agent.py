import logging
from concurrent import futures

import grpc

from contract.v1 import contract_pb2, contract_pb2_grpc

log = logging.getLogger(__name__)


class _AgentServicer(contract_pb2_grpc.AgentServiceServicer):
    """Adapta o AgentService gRPC para o método execute_task do Agent."""

    def __init__(self, agent):
        self._agent = agent

    def ExecuteTask(self, request, context):
        result = self._agent.execute_task(request.task)
        return contract_pb2.ExecuteTaskResponse(result=result)


class Agent:
    """Classe base para agentes do TG Runtime.

    Cuida do registro no Registry e do servidor gRPC do AgentService.
    Subclasses implementam apenas execute_task com a lógica de negócio.
    """

    def __init__(self, agent_id, name, capabilities, host, port, registry_addr,
                 runtime="python-sdk", contract_version="0.1.0"):
        self.agent_id = agent_id
        self.name = name
        self.capabilities = capabilities
        self.host = host
        self.port = port
        self.registry_addr = registry_addr
        self.runtime = runtime
        self.contract_version = contract_version

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

    def heartbeat(self):
        """Placeholder para o loop de heartbeat real (Fase 9)."""
        log.info("agent_id=%s heartbeat (placeholder, sem loop ainda)", self.agent_id)

    def serve(self):
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
        contract_pb2_grpc.add_AgentServiceServicer_to_server(_AgentServicer(self), server)
        server.add_insecure_port(f"[::]:{self.port}")
        server.start()
        log.info("agent_id=%s service started port=%d", self.agent_id, self.port)
        server.wait_for_termination()

    def run(self):
        self.register()
        self.serve()
