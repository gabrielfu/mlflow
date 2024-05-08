import importlib
import json
from datetime import datetime

import pytest
from packaging.version import Version

import mlflow
import mlflow.tracking.context.default_context
from mlflow.entities import SpanType
from mlflow.environment_variables import MLFLOW_TRACKING_USERNAME
from mlflow.tracing.utils import TraceJSONEncoder

from tests.tracing.conftest import clear_singleton  # noqa: F401
from tests.tracing.helper import get_traces


def test_json_deserialization(clear_singleton, monkeypatch):
    monkeypatch.setattr(mlflow.tracking.context.default_context, "_get_source_name", lambda: "test")
    monkeypatch.setenv(MLFLOW_TRACKING_USERNAME.name, "bob")
    datetime_now = datetime.now()

    class TestModel:
        @mlflow.trace()
        def predict(self, x, y):
            z = x + y
            z = self.add_one(z)
            return z  # noqa: RET504

        @mlflow.trace(
            span_type=SpanType.LLM,
            name="add_one_with_custom_name",
            attributes={
                "delta": 1,
                "metadata": {"foo": "bar"},
                # Test for non-json-serializable input
                "datetime": datetime_now,
            },
        )
        def add_one(self, z):
            return z + 1

    model = TestModel()
    model.predict(2, 5)

    trace = get_traces()[0]
    trace_json = trace.to_json()

    trace_json_as_dict = json.loads(trace_json)
    assert trace_json_as_dict == {
        "info": {
            "request_id": trace.info.request_id,
            "experiment_id": "0",
            "timestamp_ms": trace.info.timestamp_ms,
            "execution_time_ms": trace.info.execution_time_ms,
            "status": "OK",
            "request_metadata": {
                "mlflow.traceInputs": '{"x": 2, "y": 5}',
                "mlflow.traceOutputs": "8",
            },
            "tags": {
                "mlflow.traceName": "predict",
                "mlflow.source.name": "test",
                "mlflow.source.type": "LOCAL",
            },
        },
        "data": {
            "request": '{"x": 2, "y": 5}',
            "response": "8",
            "spans": [
                {
                    "name": "predict",
                    "context": {
                        "trace_id": trace.data.spans[0]._trace_id,
                        "span_id": trace.data.spans[0].span_id,
                    },
                    "parent_id": None,
                    "start_time": trace.data.spans[0].start_time_ns,
                    "end_time": trace.data.spans[0].end_time_ns,
                    "status_code": "OK",
                    "status_message": "",
                    "attributes": {
                        "mlflow.traceRequestId": json.dumps(trace.info.request_id),
                        "mlflow.spanType": '"UNKNOWN"',
                        "mlflow.spanFunctionName": '"predict"',
                        "mlflow.spanInputs": '{"x": 2, "y": 5}',
                        "mlflow.spanOutputs": "8",
                    },
                    "events": [],
                },
                {
                    "name": "add_one_with_custom_name",
                    "context": {
                        "trace_id": trace.data.spans[1]._trace_id,
                        "span_id": trace.data.spans[1].span_id,
                    },
                    "parent_id": trace.data.spans[0].span_id,
                    "start_time": trace.data.spans[1].start_time_ns,
                    "end_time": trace.data.spans[1].end_time_ns,
                    "status_code": "OK",
                    "status_message": "",
                    "attributes": {
                        "mlflow.traceRequestId": json.dumps(trace.info.request_id),
                        "mlflow.spanType": '"LLM"',
                        "mlflow.spanFunctionName": '"add_one"',
                        "mlflow.spanInputs": '{"z": 7}',
                        "mlflow.spanOutputs": "8",
                        "delta": "1",
                        "datetime": json.dumps(str(datetime_now)),
                        "metadata": '{"foo": "bar"}',
                    },
                    "events": [],
                },
            ],
        },
    }


@pytest.mark.skipif(
    importlib.util.find_spec("pydantic") is None, reason="Pydantic is not installed"
)
def test_trace_serialize_pydantic_model():
    from pydantic import BaseModel

    class MyModel(BaseModel):
        x: int
        y: str

    data = MyModel(x=1, y="foo")
    data_json = json.dumps(data, cls=TraceJSONEncoder)
    assert data_json == '{"x": 1, "y": "foo"}'
    assert json.loads(data_json) == {"x": 1, "y": "foo"}


def _is_langchain_v0_1():
    try:
        import langchain

        return Version(langchain.__version__) >= Version("0.1")
    except ImportError:
        return None


@pytest.mark.skipif(not _is_langchain_v0_1(), reason="langchain>=0.1 is not installed")
def test_trace_serialize_langchain_base_message():
    from langchain_core.messages import BaseMessage

    message = BaseMessage(
        content=[
            {
                "role": "system",
                "content": "Hello, World!",
            },
            {
                "role": "user",
                "content": "Hi!",
            },
        ],
        type="chat",
    )

    message_json = json.dumps(message, cls=TraceJSONEncoder)
    # LangChain message model contains a few more default fields actually. But we
    # only check if the following subset of the expected dictionary is present in
    # the loaded JSON rather than exact equality, because the LangChain BaseModel
    # has been changing frequently and the additional default fields may differ
    # across versions installed on developers' machines.
    expected_dict_subset = {
        "content": [
            {
                "role": "system",
                "content": "Hello, World!",
            },
            {
                "role": "user",
                "content": "Hi!",
            },
        ],
        "type": "chat",
    }
    loaded = json.loads(message_json)
    assert expected_dict_subset.items() <= loaded.items()
