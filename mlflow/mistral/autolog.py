import inspect
import logging

import mlflow
import mlflow.mistral
from mlflow.entities import SpanType
from mlflow.mistral.chat import convert_message_to_mlflow_chat, convert_tool_to_mlflow_chat_tool
from mlflow.tracing.utils import set_span_chat_messages, set_span_chat_tools
from mlflow.utils.autologging_utils.config import AutoLoggingConfig

_logger = logging.getLogger(__name__)


def construct_full_inputs(func, *args, **kwargs):
    signature = inspect.signature(func)
    # this does not create copy. So values should not be mutated directly
    arguments = signature.bind_partial(*args, **kwargs).arguments

    if "self" in arguments:
        arguments.pop("self")

    return arguments


def patched_class_call(original, self, *args, **kwargs):
    config = AutoLoggingConfig.init(flavor_name=mlflow.mistral.FLAVOR_NAME)

    if config.log_traces:
        with mlflow.start_span(
            name=f"{self.__class__.__name__}.{original.__name__}",
            span_type=SpanType.CHAT_MODEL,
        ) as span:
            inputs = construct_full_inputs(original, self, *args, **kwargs)
            span.set_inputs(inputs)

            if (tools := inputs.get("tools")) is not None:
                try:
                    tools = [convert_tool_to_mlflow_chat_tool(tool) for tool in tools]
                    set_span_chat_tools(span, tools)
                except Exception as e:
                    _logger.debug(f"Failed to set tools for {span}. Error: {e}")

            messages = [convert_message_to_mlflow_chat(msg) for msg in inputs.get("messages", [])]
            try:
                outputs = original(self, *args, **kwargs)
                span.set_outputs(outputs)
            finally:
                # Set message attribute once at the end to avoid multiple JSON serialization
                try:
                    for choice in outputs.get("choices", []):
                        choice_message = choice.get("message", {})
                        messages.append(convert_message_to_mlflow_chat(choice_message))
                    set_span_chat_messages(span, messages)
                except Exception as e:
                    _logger.debug(f"Failed to set chat messages for {span}. Error: {e}")

            return outputs
