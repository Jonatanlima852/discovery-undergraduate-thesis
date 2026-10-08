// Registro demonstrativo real; origem e limites em README.md.
(function (root) {
  const sample = {
  "label": "Exemplo registrado · failure-reassignment · 08/10/2026 · demonstração, não benchmark",
  "files": [
    {
      "name": "scenario",
      "content": "failure-reassignment\n"
    },
    {
      "name": "status",
      "content": "COMPLETED\n"
    },
    {
      "name": "environment",
      "content": "stopped\n"
    },
    {
      "name": "summary.json",
      "content": "{\n  \"scenario\": \"failure-reassignment\",\n  \"started_at\": \"2026-10-08T05:38:35.598557+00:00\",\n  \"status\": \"COMPLETED\",\n  \"elapsed_ms\": 1387.9\n}\n"
    },
    {
      "name": "result.json",
      "content": "{\n  \"scenario\": \"failure-reassignment\",\n  \"trace_id\": \"47347f1c-00e4-4f03-b301-034b664a448c\",\n  \"status\": \"COMPLETED\",\n  \"results\": {\n    \"recover\": {\n      \"task_id\": \"5cffd2b5-07b6-4155-a5ef-b66e96da889a\",\n      \"agent_id\": \"b-healthy\",\n      \"agent_kind\": \"generic\",\n      \"status\": \"TASK_STATUS_COMPLETED\",\n      \"output\": {\n        \"echo\": \"Complete após recuperar de um agente lento\"\n      },\n      \"metadata\": {},\n      \"error\": null\n    }\n  },\n  \"events\": [\n    {\n      \"type\": \"STEP_SUBMITTED\",\n      \"scenario\": \"failure-reassignment\",\n      \"step\": \"recover\",\n      \"trace_id\": \"47347f1c-00e4-4f03-b301-034b664a448c\",\n      \"timestamp\": \"2026-10-08T05:38:36.716241+00:00\",\n      \"task_id\": \"5cffd2b5-07b6-4155-a5ef-b66e96da889a\"\n    },\n    {\n      \"type\": \"STEP_FINISHED\",\n      \"scenario\": \"failure-reassignment\",\n      \"step\": \"recover\",\n      \"trace_id\": \"47347f1c-00e4-4f03-b301-034b664a448c\",\n      \"timestamp\": \"2026-10-08T05:38:36.980795+00:00\",\n      \"task_id\": \"5cffd2b5-07b6-4155-a5ef-b66e96da889a\",\n      \"agent_id\": \"b-healthy\",\n      \"status\": \"TASK_STATUS_COMPLETED\"\n    }\n  ]\n}\n"
    },
    {
      "name": "events.jsonl",
      "content": "{\"event_id\":\"b3d96a4c-f3b7-49db-acfb-6ee0beddf420\",\"task_id\":\"5cffd2b5-07b6-4155-a5ef-b66e96da889a\",\"type\":\"TASK_CREATED\",\"timestamp\":\"2026-10-08T05:38:36.74741196Z\",\"trace_id\":\"47347f1c-00e4-4f03-b301-034b664a448c\"}\n{\"event_id\":\"7dd77a26-4029-4839-afad-6c8c7517a34e\",\"task_id\":\"5cffd2b5-07b6-4155-a5ef-b66e96da889a\",\"type\":\"TASK_ASSIGNED\",\"timestamp\":\"2026-10-08T05:38:36.813401794Z\",\"agent_id\":\"a-slow\",\"trace_id\":\"47347f1c-00e4-4f03-b301-034b664a448c\",\"details\":\"attempt=1\"}\n{\"event_id\":\"171711de-49e7-45a1-8e14-ecba4059d9cc\",\"task_id\":\"5cffd2b5-07b6-4155-a5ef-b66e96da889a\",\"type\":\"TASK_TIMEOUT\",\"timestamp\":\"2026-10-08T05:38:36.916887627Z\",\"agent_id\":\"a-slow\",\"trace_id\":\"47347f1c-00e4-4f03-b301-034b664a448c\",\"details\":\"attempt=1\"}\n{\"event_id\":\"273b8cad-cc2f-499e-b506-1dfa6eb49964\",\"task_id\":\"5cffd2b5-07b6-4155-a5ef-b66e96da889a\",\"type\":\"TASK_REASSIGNED\",\"timestamp\":\"2026-10-08T05:38:36.927434752Z\",\"agent_id\":\"b-healthy\",\"trace_id\":\"47347f1c-00e4-4f03-b301-034b664a448c\",\"details\":\"attempt=2\"}\n{\"event_id\":\"5fbc06bd-0db8-46cd-92b2-97083733232d\",\"task_id\":\"5cffd2b5-07b6-4155-a5ef-b66e96da889a\",\"type\":\"TASK_COMPLETED\",\"timestamp\":\"2026-10-08T05:38:36.978420461Z\",\"agent_id\":\"b-healthy\",\"trace_id\":\"47347f1c-00e4-4f03-b301-034b664a448c\",\"details\":\"attempt=2\"}\n"
    }
  ]
};
  if (typeof module !== "undefined" && module.exports) module.exports = sample;
  else root.TGInspectorSample = sample;
})(typeof globalThis !== "undefined" ? globalThis : this);
