"""Compara BDI-only, LLM-only e LLM+BDI em missões restritas."""

from __future__ import annotations

import csv
import json
import os
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "sdk/python/src"))

from logistics import evaluate_plan, plan_mission
from tg_sdk import Scenario


def measured(operation):
    started = time.perf_counter()
    try:
        return operation(), (time.perf_counter() - started) * 1000, ""
    except Exception as error:
        return None, (time.perf_counter() - started) * 1000, str(error)


def usage_tokens(metadata):
    usage = metadata.get("usage", {}) if metadata else {}
    return int(usage.get("total_tokens", 0) or 0)


def run_bdi(scenario, case, world):
    return scenario.submit(
        f"bdi-{case['id']}",
        goal=case["request"],
        capabilities=["logistics-execution"],
        task_type="LOGISTICS_BDI_ONLY",
        payload={"world": world, "mission": case["mission"]},
    )


def run_llm(scenario, case, world):
    return scenario.submit(
        f"llm-{case['id']}",
        goal=case["request"],
        capabilities=["logistics-plan"],
        task_type="LOGISTICS_LLM_ONLY",
        payload={"world": world},
    )


def run_hybrid(scenario, case, world):
    return scenario.submit_workflow(
        case["request"],
        workflow_id=f"logistics-{case['id']}",
        final_step_id="execute",
        task_type="LOGISTICS_HYBRID",
        steps=[
            {
                "step_id": "interpret",
                "type": "INTERPRET_LOGISTICS_MISSION",
                "goal": case["request"],
                "required_capabilities": ["logistics-interpret"],
            },
            {
                "step_id": "execute",
                "type": "EXECUTE_LOGISTICS_MISSION",
                "goal": "Planeje e valide deterministicamente a missão estruturada.",
                "payload": {"world": world},
                "required_capabilities": ["logistics-execution"],
                "depends_on": ["interpret"],
                "input_bindings": [{
                    "source_step_id": "interpret",
                    "source_path": "output.mission",
                    "target_field": "mission",
                }],
            },
        ],
    )


def extract(strategy, result):
    if strategy in ("bdi-only", "llm-only"):
        result.assert_completed()
        return result.output, usage_tokens(result.metadata), None
    result.assert_completed()
    interpreted = result.steps["interpret"]["result"]
    executed = result.steps["execute"]["result"]
    return (
        executed.output,
        usage_tokens(interpreted.metadata),
        interpreted.output.get("mission"),
    )


def percentile(values, p):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[round((p / 100) * (len(ordered) - 1))]


def aggregate(rows):
    summaries = []
    for strategy in ("bdi-only", "llm-only", "hybrid"):
        selected = [row for row in rows if row["strategy"] == strategy]
        latencies = [row["latency_ms"] for row in selected]
        by_case = defaultdict(list)
        for row in selected:
            by_case[row["case_id"]].append(json.dumps(row["candidate"], sort_keys=True))
        consistent = sum(len(set(values)) == 1 for values in by_case.values())
        summaries.append({
            "strategy": strategy,
            "runs": len(selected),
            "valid_rate": sum(row["evaluation"]["valid"] for row in selected) / len(selected),
            "safe_rate": sum(row["evaluation"]["safe"] for row in selected) / len(selected),
            "optimal_rate": sum(row["evaluation"]["optimal"] for row in selected) / len(selected),
            "goal_rate": sum(row["evaluation"]["goal_reached"] for row in selected) / len(selected),
            "correct_rejection_rate": sum(row["evaluation"]["correct_rejection"] for row in selected) / len(selected),
            "runtime_success_rate": sum(not row["runtime_error"] for row in selected) / len(selected),
            "interpretation_accuracy": (
                sum(row["interpretation_exact"] for row in selected) / len(selected)
                if strategy == "hybrid" else None
            ),
            "consistency_rate": consistent / len(by_case),
            "average_latency_ms": statistics.mean(latencies),
            "p95_latency_ms": percentile(latencies, 95),
            "total_tokens": sum(row["tokens"] for row in selected),
        })
    return summaries


def write_csv(path, rows):
    fields = [
        "strategy", "runs", "valid_rate", "safe_rate", "optimal_rate", "goal_rate",
        "correct_rejection_rate", "runtime_success_rate",
        "interpretation_accuracy", "consistency_rate", "average_latency_ms",
        "p95_latency_ms", "total_tokens",
    ]
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_chart(path, summaries):
    colors = {"bdi-only": "#7c3aed", "llm-only": "#ef4444", "hybrid": "#059669"}
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="820" height="390" viewBox="0 0 820 390">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="24" y="28" font-family="sans-serif" font-size="17">Validade, segurança e consistência por estratégia</text>',
    ]
    metrics = [("valid_rate", "planos válidos"), ("optimal_rate", "planos ótimos"), ("consistency_rate", "consistência")]
    for group, (field, label) in enumerate(metrics):
        base_x = 70 + group * 250
        parts.append(f'<text x="{base_x + 80}" y="350" text-anchor="middle" font-family="sans-serif" font-size="12">{label}</text>')
        for index, row in enumerate(summaries):
            value = row[field]
            height = value * 250
            x = base_x + index * 55
            y = 320 - height
            parts.append(f'<rect x="{x}" y="{y:.1f}" width="42" height="{height:.1f}" fill="{colors[row["strategy"]]}"/>')
            parts.append(f'<text x="{x+21}" y="{y-6:.1f}" text-anchor="middle" font-family="sans-serif" font-size="10">{value*100:.0f}%</text>')
    for index, row in enumerate(summaries):
        x = 270 + index * 120
        parts.append(f'<rect x="{x}" y="370" width="12" height="12" fill="{colors[row["strategy"]]}"/>')
        parts.append(f'<text x="{x+17}" y="380" font-family="sans-serif" font-size="11">{row["strategy"]}</text>')
    parts.append('</svg>')
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def main():
    world = json.loads((ROOT / "logistics/world.json").read_text())
    cases = json.loads((ROOT / "logistics/cases.json").read_text())
    repetitions = int(os.getenv("LOGISTICS_REPETITIONS", "2"))
    output_dir = Path(os.getenv("LOGISTICS_OUTPUT_DIR", ROOT / "benchmarks/results/logistics-current"))
    output_dir.mkdir(parents=True, exist_ok=True)
    address = os.getenv("ORCHESTRATOR_ADDR", "localhost:54052")
    rows = []

    with Scenario("logistics-benchmark", address) as scenario:
        for repetition in range(1, repetitions + 1):
            for case in cases:
                oracle = plan_mission(world, case["mission"])
                for strategy, operation in (
                    ("bdi-only", lambda c=case: run_bdi(scenario, c, world)),
                    ("llm-only", lambda c=case: run_llm(scenario, c, world)),
                    ("hybrid", lambda c=case: run_hybrid(scenario, c, world)),
                ):
                    result, latency, runtime_error = measured(operation)
                    candidate, tokens, interpreted = {}, 0, None
                    if result is not None:
                        try:
                            candidate, tokens, interpreted = extract(strategy, result)
                        except Exception as error:
                            runtime_error = runtime_error or str(error)
                    evaluation = evaluate_plan(world, case["mission"], candidate)
                    if runtime_error:
                        evaluation = {
                            **evaluation,
                            "valid": False,
                            "safe": False,
                            "goal_reached": False,
                            "correct_rejection": False,
                            "optimal": False,
                            "optimality_gap_minutes": None,
                            "failure_reason": f"runtime: {runtime_error}",
                        }
                    row = {
                        "case_id": case["id"],
                        "repetition": repetition,
                        "strategy": strategy,
                        "request": case["request"],
                        "expected_mission": case["mission"],
                        "oracle": oracle,
                        "candidate": candidate,
                        "evaluation": evaluation,
                        "interpretation": interpreted,
                        "interpretation_exact": interpreted == case["mission"] if interpreted else False,
                        "latency_ms": latency,
                        "tokens": tokens,
                        "runtime_error": runtime_error,
                    }
                    rows.append(row)
                    print(
                        f"{strategy:8} case={case['id']:24} rep={repetition} "
                        f"valid={evaluation['valid']} latency_ms={latency:.1f}",
                        flush=True,
                    )

    summaries = aggregate(rows)
    document = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": os.getenv("LLM_MODEL", "gpt-5.6-luna"),
        "repetitions": repetitions,
        "case_count": len(cases),
        "method": "ground-truth mission and deterministic action simulator",
        "rows": rows,
        "summary": summaries,
    }
    (output_dir / "logistics-results.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_csv(output_dir / "logistics-summary.csv", summaries)
    write_chart(output_dir / "logistics-quality.svg", summaries)
    print(json.dumps(summaries, indent=2), flush=True)
    print(f"LOGISTICS BENCHMARK COMPLETE output={output_dir}", flush=True)


if __name__ == "__main__":
    main()
