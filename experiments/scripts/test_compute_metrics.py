import unittest

from compute_metrics import summarize_task


class RecoveryMetricsTests(unittest.TestCase):
    def test_summarizes_recovery_and_reassignment(self):
        events = [
            {"task_id": "task-1", "trace_id": "trace-1", "type": "TASK_CREATED", "timestamp": "2026-10-03T12:00:00+00:00"},
            {"task_id": "task-1", "type": "TASK_ASSIGNED", "timestamp": "2026-10-03T12:00:00.010000+00:00"},
            {"task_id": "task-1", "type": "TASK_TIMEOUT", "timestamp": "2026-10-03T12:00:00.110000+00:00"},
            {"task_id": "task-1", "type": "TASK_REASSIGNED", "timestamp": "2026-10-03T12:00:00.125000+00:00"},
            {"task_id": "task-1", "type": "TASK_COMPLETED", "timestamp": "2026-10-03T12:00:00.150000+00:00"},
        ]

        row = summarize_task("task-1", events)

        self.assertEqual(row["recovery_ms"], 15)
        self.assertEqual(row["reassignment_count"], 1)
        self.assertEqual(row["status"], "TASK_COMPLETED")


if __name__ == "__main__":
    unittest.main()
