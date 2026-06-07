import argparse
import csv
import json
from datetime import datetime

CREATED = "TASK_CREATED"
ASSIGNED = "TASK_ASSIGNED"
COMPLETED = "TASK_COMPLETED"
FAILED = "TASK_FAILED"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Calcula métricas de latência a partir de um events.jsonl"
    )
    parser.add_argument("--events", required=True, help="Caminho para o events.jsonl")
    parser.add_argument(
        "--output",
        default="experiments/results/summary.csv",
        help="Caminho do summary.csv de saída (default: experiments/results/summary.csv)",
    )
    return parser.parse_args()


def load_events_by_task(path):
    tasks = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            event = json.loads(line)
            task_id = event["task_id"]
            tasks.setdefault(task_id, []).append(event)
    return tasks


def parse_timestamp(value):
    return datetime.fromisoformat(value)


def ms_between(start, end):
    return (end - start).total_seconds() * 1000


def summarize_task(task_id, events):
    by_type = {}
    for event in events:
        by_type[event["type"]] = event

    created = by_type.get(CREATED)
    assigned = by_type.get(ASSIGNED)
    finished = by_type.get(COMPLETED) or by_type.get(FAILED)

    if created is None:
        return None

    created_at = parse_timestamp(created["timestamp"])
    assigned_at = parse_timestamp(assigned["timestamp"]) if assigned else None
    finished_at = parse_timestamp(finished["timestamp"]) if finished else None

    status = finished["type"] if finished else "IN_PROGRESS"
    trace_id = created.get("trace_id", "")

    assignment_latency_ms = ms_between(created_at, assigned_at) if assigned_at else None
    execution_latency_ms = (
        ms_between(assigned_at, finished_at) if assigned_at and finished_at else None
    )
    total_latency_ms = ms_between(created_at, finished_at) if finished_at else None

    return {
        "task_id": task_id,
        "trace_id": trace_id,
        "status": status,
        "created_at": created["timestamp"],
        "assigned_at": assigned["timestamp"] if assigned else "",
        "completed_at": finished["timestamp"] if finished else "",
        "assignment_latency_ms": assignment_latency_ms,
        "execution_latency_ms": execution_latency_ms,
        "total_latency_ms": total_latency_ms,
    }


def percentile(values, p):
    if not values:
        return None
    ordered = sorted(values)
    index = int(round((p / 100) * (len(ordered) - 1)))
    return ordered[index]


def print_aggregate(rows):
    total = len(rows)
    completed = [row for row in rows if row["status"] == COMPLETED]
    latencies = [row["total_latency_ms"] for row in completed if row["total_latency_ms"] is not None]

    print(f"tasks totais:      {total}")
    print(f"tasks completadas: {len(completed)}")
    if total:
        print(f"taxa de sucesso:   {len(completed) / total:.1%}")
    if latencies:
        print(f"latência total (ms) — média: {sum(latencies) / len(latencies):.1f}, "
              f"mín: {min(latencies):.1f}, máx: {max(latencies):.1f}, "
              f"p50: {percentile(latencies, 50):.1f}, p95: {percentile(latencies, 95):.1f}")


def write_csv(path, rows):
    fieldnames = [
        "task_id",
        "trace_id",
        "status",
        "created_at",
        "assigned_at",
        "completed_at",
        "assignment_latency_ms",
        "execution_latency_ms",
        "total_latency_ms",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    args = parse_args()
    tasks = load_events_by_task(args.events)

    rows = []
    for task_id, events in tasks.items():
        row = summarize_task(task_id, events)
        if row is not None:
            rows.append(row)

    write_csv(args.output, rows)
    print(f"summary.csv gerado em: {args.output}\n")
    print_aggregate(rows)


if __name__ == "__main__":
    main()
