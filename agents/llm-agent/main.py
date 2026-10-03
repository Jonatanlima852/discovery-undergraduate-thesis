import json

from pydantic import BaseModel, ConfigDict, Field

from tg_sdk import LlmAgent, Prompt, llm_capability


class SubtaskDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str
    required_capabilities: list[str]
    payload_json: str = Field(
        description="JSON object serialized as a string; use {} when empty"
    )


class Decomposition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subtasks: list[SubtaskDraft] = Field(min_length=1, max_length=10)
    reasoning_summary: str
    confidence: float = Field(ge=0.0, le=1.0)


class Explanation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    explanation: str
    reasoning_summary: str
    confidence: float = Field(ge=0.0, le=1.0)


def normalize_decomposition(plan):
    subtasks = []
    for subtask in plan.subtasks:
        payload = json.loads(subtask.payload_json)
        if not isinstance(payload, dict):
            raise ValueError("payload_json must decode to an object")
        subtasks.append(
            {
                "goal": subtask.goal,
                "required_capabilities": subtask.required_capabilities,
                "payload": payload,
            }
        )
    return {
        "subtasks": subtasks,
        "reasoning_summary": plan.reasoning_summary,
        "confidence": plan.confidence,
    }


class PlannerExplainerAgent(LlmAgent):
    capabilities = ["task-decomposition", "explanation"]
    default_agent_id = "llm-agent-01"
    default_name = "LLM Planner and Explainer"
    default_port = 60056

    @llm_capability(
        "task-decomposition",
        output_schema=Decomposition,
        result_mapper=normalize_decomposition,
    )
    def decompose(self, goal, context):
        return Prompt(
            system=(
                "Decompose the goal into executable subtasks. Capabilities are "
                "short stable IDs such as route-planning, meeting-scheduling, "
                "echo, or explanation. For route-planning, payload_json must "
                "contain origin and destination. Never create operational IDs. "
                "Return a concise public reasoning summary."
            ),
            user=goal,
        )

    @llm_capability("explanation", output_schema=Explanation)
    def explain(self, goal, context):
        return Prompt(
            system=(
                "Explain the supplied result clearly in Portuguese. Treat the "
                "context as authoritative: do not alter route, distance, or "
                "selected plan values. Return only a public reasoning summary."
            ),
            user=(
                f"Objetivo: {goal}\n"
                f"Contexto JSON: {json.dumps(context, ensure_ascii=False)}"
            ),
        )


if __name__ == "__main__":
    PlannerExplainerAgent.from_env().run()
