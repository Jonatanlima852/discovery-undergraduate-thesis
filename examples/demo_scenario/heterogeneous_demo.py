"""Cenário transitório LLM -> BDI -> LLM usando a API pública do SDK.

O encadeamento permanece no cliente até o orchestrator suportar workflows,
mas detalhes de protobuf, gRPC, IDs e trace ficam isolados em Scenario.
"""

import json
import os
import re
import sys

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "../../sdk/python/src"),
)

from tg_sdk import Scenario

GOAL = "Planeje uma rota de A para D e explique por que ela foi escolhida"
ROUTE_PATTERN = re.compile(
    r"(?:de|from)\s+(?P<origin>[\w-]+)\s+(?:para|to)\s+(?P<destination>[\w-]+)",
    re.IGNORECASE,
)


def route_request(plan):
    for subtask in plan["subtasks"]:
        if "route-planning" not in subtask["required_capabilities"]:
            continue
        payload = subtask.get("payload", {})
        origin = payload.get("origin") or payload.get("origem")
        destination = payload.get("destination") or payload.get("destino")
        if not origin or not destination:
            match = ROUTE_PATTERN.search(subtask["goal"]) or ROUTE_PATTERN.search(GOAL)
            if not match:
                raise RuntimeError("LLM não informou origem e destino")
            origin = match.group("origin")
            destination = match.group("destination")
        return subtask, str(origin), str(destination)
    raise RuntimeError("LLM não produziu uma subtask route-planning")


def show(step, result):
    print(f"\n=== {step} ===")
    print(f"agent_id: {result.agent_id}")
    print(f"status: {result.status}")
    print(json.dumps(result.output, ensure_ascii=False, indent=2))
    if result.metadata:
        print("metadata:")
        print(json.dumps(result.metadata, ensure_ascii=False, indent=2))


def main():
    address = os.getenv("ORCHESTRATOR_ADDR", "localhost:50052")
    with Scenario("heterogeneous-route", address) as scenario:
        decomposition = scenario.submit(
            "decompose",
            goal=GOAL,
            capabilities=["task-decomposition"],
            task_type="NATURAL_LANGUAGE",
        ).assert_completed()
        show("1. LLM decompõe o objetivo", decomposition)

        subtask, origin, destination = route_request(decomposition.output)
        route = scenario.submit(
            "route",
            goal=subtask["goal"],
            capabilities=["route-planning"],
            task_type="PLAN_ROUTE",
            payload={"origin": origin, "destination": destination},
            bdi_goal=f"ir de {origin} para {destination}",
        ).assert_completed()
        show("2. BDI seleciona e executa o plano", route)

        explanation = scenario.submit(
            "explain",
            goal="Explique em português a decisão BDI sem alterar seus dados.",
            capabilities=["explanation"],
            task_type="EXPLANATION",
            payload={
                "original_goal": GOAL,
                "bdi_result": route.output,
                "bdi_metadata": route.metadata,
            },
        ).assert_completed()
        show("3. LLM explica a decisão do BDI", explanation)

        assert route.metadata["selected_plan"] == "via_intermediate"
        assert route.output["route"] == ["A", "B", "D"]
        assert route.output["distance"] == 25
        print(f"\nCENÁRIO APROVADO trace_id={scenario.trace_id}")


if __name__ == "__main__":
    main()
