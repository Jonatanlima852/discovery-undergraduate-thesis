from google.protobuf import struct_pb2, timestamp_pb2

from contract.v1 import contract_pb2

from tg_sdk.agent import Agent


def _now():
    ts = timestamp_pb2.Timestamp()
    ts.GetCurrentTime()
    return ts


class BdiAgent(Agent):
    """Classe base para agentes que raciocinam no estilo BDI
    (Beliefs, Desires, Intentions).

    Generaliza o ciclo comum a esse tipo de agente — extrair o desejo da
    task, escolher um plano de uma biblioteca com base nas crenças, e
    devolver o resultado com o plano escolhido e o raciocínio — para que
    subclasses só precisem fornecer:

      beliefs       → a base de crenças do agente (qualquer estrutura;
                       é repassada como está para os planos)
      plan_library  → lista ordenada de planos: funções (desire, beliefs)
                       -> dict com {"name", "reasoning_summary", "output"}
                       ou None se o plano não se aplica
      extract_desire(task) → devolve o desejo extraído da task, ou None
                       se a task não contiver as informações necessárias
    """

    def __init__(self, *args, beliefs=None, plan_library=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.beliefs = {} if beliefs is None else beliefs
        self.plan_library = list(plan_library or [])

    # --- pontos de extensão: subclasses devem sobrescrever ---

    def extract_desire(self, task):
        """Lê o desejo do agente a partir da task (ex.: campos do payload,
        ou — quando presente — task.bdi.goal).

        Devolve o desejo (qualquer estrutura que os planos entendam) ou
        None se a task não tiver as informações necessárias.
        """
        raise NotImplementedError("subclasses devem implementar extract_desire")

    def merge_external_beliefs(self, beliefs_text):
        """Hook opcional: interpreta task.bdi.beliefs (texto livre,
        formato decidido por quem o preencheu) e mescla em self.beliefs.

        Existe para permitir que outro agente do sistema — um agente LLM,
        por exemplo — entregue crenças prontas através do contrato comum
        (BdiExtension.beliefs), demonstrando troca estruturada de
        raciocínio entre agentes heterogêneos.

        Por padrão não faz nada: o formato de beliefs é específico de
        cada agente, então a interpretação fica a cargo da subclasse.
        """

    # --- consumo opcional de Task.bdi (BdiExtension) ---

    def _apply_external_bdi(self, task):
        """Se a task chegar com BdiExtension preenchida, dá à subclasse
        a chance de incorporar as crenças externas antes de deliberar."""
        if not task.HasField("bdi"):
            return
        if task.bdi.beliefs:
            self.merge_external_beliefs(task.bdi.beliefs)

    # --- comportamento genérico de seleção e execução ---

    def select_plan(self, desire):
        """Avalia todos os planos aplicáveis da biblioteca e escolhe a
        intenção do agente — o melhor entre eles, não o primeiro.

        Cada plano pode opcionalmente trazer um campo numérico "cost"
        (quanto menor, melhor — ex.: distância, tempo, número de passos).
        Se algum plano aplicável tiver "cost", vence o de menor custo.
        Caso nenhum traga "cost", mantemos o critério mais simples — o
        primeiro aplicável, na ordem da biblioteca — para não forçar
        planos sem noção de custo a competir entre si.

        Devolve None se nenhum plano se aplicar.
        """
        applicable = []
        for plan_fn in self.plan_library:
            plan = plan_fn(desire, self.beliefs)
            if plan is not None:
                applicable.append(plan)

        if not applicable:
            return None

        with_cost = [plan for plan in applicable if plan.get("cost") is not None]
        if with_cost:
            return min(with_cost, key=lambda plan: plan["cost"])

        return applicable[0]

    def execute_task(self, task):
        self._apply_external_bdi(task)

        desire = self.extract_desire(task)
        if desire is None:
            return self._failed_result(
                task,
                code=contract_pb2.ERROR_CODE_INVALID_TASK,
                message="não foi possível extrair o desejo da task (payload incompleto)",
                retryable=False,
            )

        plan = self.select_plan(desire)
        if plan is None:
            return self._failed_result(
                task,
                code=contract_pb2.ERROR_CODE_EXECUTION_FAILED,
                message="nenhum plano da biblioteca se aplica a esse desejo",
                retryable=False,
            )

        return self._completed_result(task, plan)

    # --- montagem do TaskResult ---

    def _completed_result(self, task, plan):
        output = struct_pb2.Struct()
        output.update(plan.get("output", {}))

        metadata_fields = {
            "selected_plan": plan["name"],
            "reasoning_summary": plan["reasoning_summary"],
        }
        # se quem submeteu a task já trouxe um intention_id (BdiExtension),
        # devolvemos o mesmo identificador — permite correlacionar a
        # intenção combinada entre agentes através do contrato comum
        if task.HasField("bdi") and task.bdi.intention_id:
            metadata_fields["intention_id"] = task.bdi.intention_id

        metadata = struct_pb2.Struct()
        metadata.update(metadata_fields)

        return contract_pb2.TaskResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            status=contract_pb2.TASK_STATUS_COMPLETED,
            completed_at=_now(),
            trace=task.trace,
            output=output,
            metadata=metadata,
        )

    def _failed_result(self, task, code, message, retryable):
        return contract_pb2.TaskResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            status=contract_pb2.TASK_STATUS_FAILED,
            completed_at=_now(),
            trace=task.trace,
            error=contract_pb2.ErrorInfo(code=code, message=message, retryable=retryable),
        )
