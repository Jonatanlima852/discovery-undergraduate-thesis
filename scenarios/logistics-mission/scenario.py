"""Demonstra uma missão natural interpretada pela LLM e executada pelo BDI."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "sdk/python/src"))

from benchmarks.logistics import run_hybrid
from logistics import evaluate_plan
from tg_sdk import Scenario


def main():
    world = json.loads((ROOT / "logistics/world.json").read_text())
    cases = json.loads((ROOT / "logistics/cases.json").read_text())
    case = next(item for item in cases if item["id"] == "avoid-contamination")
    address = os.getenv("ORCHESTRATOR_ADDR", "localhost:54052")

    with Scenario("logistics-golden-example", address) as scenario:
        result = run_hybrid(scenario, case, world).assert_completed()

    candidate = result.steps["execute"]["result"].output
    evaluation = evaluate_plan(world, case["mission"], candidate)
    if not evaluation["valid"]:
        raise AssertionError(evaluation["failure_reason"])

    print("Solicitação:", case["request"])
    print("Interpretação LLM:")
    print(json.dumps(result.steps["interpret"]["result"].output, indent=2, ensure_ascii=False))
    print("Plano BDI validado:")
    print(json.dumps(candidate, indent=2, ensure_ascii=False))
    print("Avaliação independente:")
    print(json.dumps(evaluation, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
