import logging
import os
from dataclasses import dataclass

from google.protobuf import json_format, struct_pb2, timestamp_pb2
from pydantic import BaseModel

from contract.v1 import contract_pb2
from tg_sdk.agent import Agent

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


def _now():
    value = timestamp_pb2.Timestamp()
    value.GetCurrentTime()
    return value


def _struct(value):
    message = struct_pb2.Struct()
    message.update(value)
    return message


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

    def execute_task(self, task):
        retryable = False
        try:
            capability = self._requested_capability(task)
            handler, declaration = self._handlers[capability]
            context = (
                json_format.MessageToDict(task.payload)
                if task.HasField("payload")
                else {}
            )
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
            return contract_pb2.TaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status=contract_pb2.TASK_STATUS_COMPLETED,
                completed_at=_now(),
                trace=task.trace,
                output=_struct(output),
                metadata=_struct({"provider": "openai", "model": self.model}),
            )

        return contract_pb2.TaskResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            status=contract_pb2.TASK_STATUS_FAILED,
            completed_at=_now(),
            trace=task.trace,
            error=contract_pb2.ErrorInfo(
                code=contract_pb2.ERROR_CODE_EXECUTION_FAILED,
                message=message,
                retryable=retryable,
            ),
        )
