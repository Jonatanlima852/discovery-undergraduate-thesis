import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from tg_sdk import LlmAgent, Prompt, llm_capability


class ResultBindingDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_step_id: str
    source_path: str
    target_field: str


class WorkflowStepDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str
    type: str
    goal: str
    payload_json: str = Field(description="JSON object serialized as a string")
    required_capabilities: list[str] = Field(min_length=1)
    depends_on: list[str]
    input_bindings: list[ResultBindingDraft]
    bdi_goal: str = ""


class WorkflowDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_id: str
    final_step_id: str
    steps: list[WorkflowStepDraft] = Field(min_length=1, max_length=10)


class Explanation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    explanation: str
    reasoning_summary: str
    confidence: float = Field(ge=0.0, le=1.0)


class LogisticsAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal[
        "PICK_UP_PACKAGE", "PICK_UP_KEY", "RECHARGE", "UNLOCK_DOOR",
        "MOVE", "DELIVER_PACKAGE",
    ]
    origin: str = ""
    destination: str = ""
    location: str = ""


class LogisticsPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feasible: bool
    actions: list[LogisticsAction]
    rejection_reason: str = ""


class LogisticsMission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destination: str
    forbidden_locations: list[str]
    required_locations: list[str]
    minimum_final_battery: int = Field(ge=0, le=100)
    deadline_minutes: int = Field(gt=0)


class LogisticsInterpretation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mission: LogisticsMission


def normalize_logistics_plan(plan):
    actions = []
    for declared in plan.actions:
        action = {"type": declared.type}
        if declared.type == "MOVE":
            action.update({"from": declared.origin, "to": declared.destination})
        elif declared.location:
            action["location"] = declared.location
        actions.append(action)
    return {
        "feasible": plan.feasible,
        "actions": actions,
        "rejection_reason": plan.rejection_reason,
    }


def normalize_workflow(plan):
    steps = []
    for step in plan.steps:
        payload = json.loads(step.payload_json)
        if not isinstance(payload, dict):
            raise ValueError("payload_json must decode to an object")
        steps.append(
            {
                "step_id": step.step_id,
                "type": step.type,
                "goal": step.goal,
                "payload": payload,
                "required_capabilities": step.required_capabilities,
                "depends_on": step.depends_on,
                "input_bindings": [
                    binding.model_dump() for binding in step.input_bindings
                ],
                "bdi_goal": step.bdi_goal,
            }
        )
    return {
        "workflow_id": plan.workflow_id,
        "final_step_id": plan.final_step_id,
        "steps": steps,
    }


class PlannerExplainerAgent(LlmAgent):
    capabilities = [
        "task-decomposition", "explanation", "logistics-plan",
        "logistics-interpret",
    ]
    default_agent_id = "llm-agent-01"
    default_name = "LLM Planner and Explainer"
    default_port = 60056

    @llm_capability(
        "task-decomposition",
        output_schema=WorkflowDraft,
        result_mapper=normalize_workflow,
    )
    def decompose(self, goal, context):
        return Prompt(
            system=(
                "Create a finite executable workflow DAG. Capabilities are short "
                "stable IDs such as route-planning, meeting-scheduling, echo, "
                "or explanation. Never use task-decomposition inside a step. "
                "For route requests, create exactly a route-planning step with "
                "step_id route followed by an explanation step with step_id "
                "explain, and make explain the final_step_id. Put origin and "
                "destination in the first "
                "payload_json, set bdi_goal, and bind its complete output to "
                "bdi_result plus metadata to bdi_metadata in the explanation "
                "payload. Bindings may read output, metadata, status or agent_id. "
                "Use at most 10 steps and depth 5. Never create operational IDs."
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

    @llm_capability(
        "logistics-plan",
        output_schema=LogisticsPlan,
        result_mapper=normalize_logistics_plan,
    )
    def logistics_plan(self, goal, context):
        return Prompt(
            system=(
                "You are the sole planner for a logistics robot. Produce a complete "
                "executable action sequence from the supplied world JSON and natural "
                "request. Respect graph edges, energy, elapsed minutes, forbidden and "
                "required locations, the locked F door, package/key locations, final "
                "battery and deadline. MOVE uses origin/destination; other actions use "
                "location. Never invent an edge. If no valid sequence exists, set "
                "feasible=false and return no actions. Do not assume an external "
                "validator or symbolic planner will repair your answer."
            ),
            user=(
                f"Natural request: {goal}\n"
                f"World JSON: {json.dumps(context.get('world'), sort_keys=True)}"
            ),
        )

    @llm_capability("logistics-interpret", output_schema=LogisticsInterpretation)
    def logistics_interpret(self, goal, context):
        return Prompt(
            system=(
                "Extract the logistics mission literally. Valid locations are A through "
                "H. Do not plan actions and do not weaken constraints. Percent battery "
                "maps to minimum_final_battery. If no forbidden/required places are "
                "stated, use empty lists. Return the explicit destination and deadline."
            ),
            user=goal,
        )


if __name__ == "__main__":
    PlannerExplainerAgent.from_env().run()
