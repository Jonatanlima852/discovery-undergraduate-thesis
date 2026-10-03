import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Mapping

from pydantic import BaseModel

from tg_sdk.agent import Agent
from tg_sdk.models import Task, TaskResult

log = logging.getLogger(__name__)


class LlmValidationError(ValueError):
    pass


@dataclass(frozen=True)
class Prompt:
    system: str
    user: str


def llm_capability(capability_id, *, output_schema, result_mapper=None):
    """Declara uma capability OpenAI com saída estruturada.

    ``output_schema`` é um modelo Pydantic entregue ao Responses API.
    ``result_mapper`` é opcional e converte o modelo validado em um dict
    de domínio antes de o SDK montar o ``TaskResult``.
    """
    if not isinstance(output_schema, type) or not issubclass(output_schema, BaseModel):
        raise TypeError("output_schema must be a Pydantic BaseModel class")

    def decorate(method):
        method._tg_llm_capability = {
            "id": capability_id,
            "output_schema": output_schema,
            "result_mapper": result_mapper,
        }
        return method

    return decorate


_OPERATIONAL_FIELDS = {
    "task_id",
    "agent_id",
    "assigned_agent_id",
    "trace",
    "trace_id",
    "span_id",
    "parent_span_id",
    "status",
    "attempt",
    "retry_policy",
    "selection_policy",
    "created_at",
    "completed_at",
}


def _reject_operational_fields(value: Any, path="output"):
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if key in _OPERATIONAL_FIELDS:
                raise LlmValidationError(
                    f"model output cannot define operational field: {path}.{key}"
                )
            _reject_operational_fields(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _reject_operational_fields(nested, f"{path}[{index}]")


def _usage_metadata(response):
    usage = getattr(response, "usage", None)
    if usage is None:
        return {}
    if hasattr(usage, "model_dump"):
        usage = usage.model_dump()
    elif not isinstance(usage, Mapping):
        usage = {
            key: getattr(usage, key)
            for key in ("input_tokens", "output_tokens", "total_tokens")
            if getattr(usage, key, None) is not None
        }
    return {key: value for key, value in dict(usage).items() if value is not None}


class LlmAgent(Agent):
    """Agente OpenAI com contrato, dispatch e structured output no SDK."""

    runtime_name = "python-sdk-openai"
    model = "gpt-5.6-luna"

    def __init__(self, model=None, openai_client=None, **kwargs):
        super().__init__(**kwargs)
        self.model = model or os.getenv("LLM_MODEL", type(self).model)
        if openai_client is None:
            from openai import OpenAI

            openai_client = OpenAI()
        self._openai = openai_client
        self._handlers = self._discover_handlers()

    def _discover_handlers(self):
        handlers = {}
        for name in dir(self):
            method = getattr(self, name)
            declaration = getattr(method, "_tg_llm_capability", None)
            if declaration is None:
                continue
            capability = declaration["id"]
            if capability in handlers:
                raise ValueError(f"duplicate LLM capability: {capability}")
            handlers[capability] = (method, declaration)
        return handlers

    def _requested_capability(self, task):
        requested = [
            item for item in task.required_capabilities if item in self._handlers
        ]
        if len(requested) != 1:
            raise LlmValidationError(
                "task must request exactly one supported LLM capability"
            )
        return requested[0]

    def handle(self, task: Task) -> TaskResult:
        retryable = False
        started = time.perf_counter()
        try:
            capability = self._requested_capability(task)
            handler, declaration = self._handlers[capability]
            context = dict(task.payload)
            prompt = handler(task.goal, context)
            if not isinstance(prompt, Prompt):
                raise LlmValidationError("LLM capability handler must return Prompt")

            response = self._openai.responses.parse(
                model=self.model,
                input=[
                    {"role": "system", "content": prompt.system},
                    {"role": "user", "content": prompt.user},
                ],
                text_format=declaration["output_schema"],
            )
            parsed = response.output_parsed
            if parsed is None:
                raise LlmValidationError(
                    "OpenAI response did not contain structured output"
                )

            mapper = declaration["result_mapper"]
            output = mapper(parsed) if mapper else parsed.model_dump()
            if not isinstance(output, dict):
                raise LlmValidationError("result_mapper must return an object")
            _reject_operational_fields(output)
        except (LlmValidationError, ValueError) as error:
            message = str(error)
        except Exception as error:
            log.exception(
                "OpenAI call failed task_id=%s error_type=%s",
                task.task_id,
                type(error).__name__,
            )
            message = f"OpenAI call failed ({type(error).__name__})"
            retryable = True
        else:
            metadata = {
                "provider": "openai",
                "model": self.model,
                "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            }
            usage = _usage_metadata(response)
            if usage:
                metadata["usage"] = usage
            return TaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="TASK_STATUS_COMPLETED",
                trace=task.trace,
                output=output,
                metadata=metadata,
            )

        return TaskResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            status="TASK_STATUS_FAILED",
            trace=task.trace,
            error_code="ERROR_CODE_EXECUTION_FAILED",
            error_message=message,
            retryable=retryable,
        )

    def execute_task(self, task):
        """Compatibilidade temporária com chamadas locais baseadas em protobuf."""
        friendly = task if isinstance(task, Task) else Task.from_proto(task)
        result = self.handle(friendly)
        return result if isinstance(task, Task) else result.to_proto()
