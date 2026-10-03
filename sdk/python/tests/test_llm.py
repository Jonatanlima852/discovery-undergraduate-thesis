import unittest

from google.protobuf import struct_pb2
from pydantic import BaseModel, ConfigDict

from contract.v1 import contract_pb2
from tg_sdk import LlmAgent, Prompt, llm_capability


class StrictOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str


class _FakeResponses:
    def __init__(self, parsed):
        self.parsed = parsed
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return type("Response", (), {"output_parsed": self.parsed})()


class _FakeOpenAI:
    def __init__(self, parsed):
        self.responses = _FakeResponses(parsed)


class StructuredAgent(LlmAgent):
    capabilities = ["structured"]

    @llm_capability("structured", output_schema=StrictOutput)
    def structured(self, goal, context):
        return Prompt(system="Return the value.", user=goal)


def make_task():
    payload = struct_pb2.Struct()
    payload.update({"input": "A"})
    return contract_pb2.Task(
        task_id="task-llm",
        goal="Extract A",
        payload=payload,
        required_capabilities=["structured"],
        trace=contract_pb2.TraceContext(trace_id="trace-llm"),
    )


class OpenAiLlmTests(unittest.TestCase):
    def build_agent(self, parsed):
        client = _FakeOpenAI(parsed)
        agent = StructuredAgent(
            agent_id="llm",
            name="LLM",
            capabilities=["structured"],
            host="localhost",
            port=60000,
            registry_addr="localhost:50051",
            model="test-model",
            openai_client=client,
        )
        return agent, client

    def test_uses_responses_parse_with_declared_schema(self):
        agent, client = self.build_agent(StrictOutput(value="A"))

        result = agent.execute_task(make_task())

        self.assertEqual(result.status, contract_pb2.TASK_STATUS_COMPLETED)
        self.assertEqual(result.output["value"], "A")
        call = client.responses.calls[0]
        self.assertEqual(call["model"], "test-model")
        self.assertIs(call["text_format"], StrictOutput)

    def test_missing_structured_output_returns_stable_failure(self):
        agent, _ = self.build_agent(None)

        result = agent.execute_task(make_task())

        self.assertEqual(result.status, contract_pb2.TASK_STATUS_FAILED)
        self.assertIn("structured output", result.error.message)
        self.assertFalse(result.error.retryable)


if __name__ == "__main__":
    unittest.main()
