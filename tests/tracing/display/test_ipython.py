import json
from unittest.mock import Mock

import mlflow
from mlflow.tracing.display import get_display_handler

from tests.tracing.helper import create_trace


class MockIPython:
    def __init__(self):
        self.execution_count = 0

    def mock_run_cell(self):
        self.execution_count += 1


def test_display_is_not_called_without_ipython(monkeypatch):
    # in an IPython environment, the interactive shell will
    # be returned. however, for test purposes, just mock that
    # the value is not None.
    mock_display = Mock()
    monkeypatch.setattr("IPython.display.display", mock_display)
    handler = get_display_handler()

    handler.display_traces([create_trace("a")])
    assert mock_display.call_count == 0

    monkeypatch.setattr("IPython.get_ipython", lambda: MockIPython())
    handler.display_traces([create_trace("b")])
    assert mock_display.call_count == 1


def test_ipython_client_only_logs_once_per_execution(monkeypatch):
    mock_ipython = MockIPython()
    monkeypatch.setattr("IPython.get_ipython", lambda: mock_ipython)
    handler = get_display_handler()

    mock_display_handle = Mock()
    mock_display = Mock(return_value=mock_display_handle)
    monkeypatch.setattr("IPython.display.display", mock_display)
    handler.display_traces([create_trace("a")])
    handler.display_traces([create_trace("b")])
    handler.display_traces([create_trace("c")])

    # there should be one display and two updates
    assert mock_display.call_count == 1
    assert mock_display_handle.update.call_count == 2

    # after incrementing the execution count,
    # the next log should call display again
    mock_ipython.mock_run_cell()
    handler.display_traces([create_trace("a")])
    assert mock_display.call_count == 2


def test_display_is_called_in_correct_functions(monkeypatch):
    mock_ipython = MockIPython()
    monkeypatch.setattr("IPython.get_ipython", lambda: mock_ipython)
    handler = get_display_handler()

    mock_display_handle = Mock()
    mock_display = Mock(return_value=mock_display_handle)
    monkeypatch.setattr("IPython.display.display", mock_display)
    trace = create_trace("a")
    handler.display_traces([trace])
    assert mock_display.call_count == 1

    class MockMlflowClient:
        def search_traces(self, *args, **kwargs):
            return [create_trace("a"), create_trace("b"), create_trace("c")]

    monkeypatch.setattr("mlflow.tracing.fluent.MlflowClient", MockMlflowClient)

    mock_ipython.mock_run_cell()
    mlflow.search_traces(["123"])
    assert mock_display.call_count == 2


def test_display_deduplicates_traces(monkeypatch):
    mock_ipython = MockIPython()
    monkeypatch.setattr("IPython.get_ipython", lambda: mock_ipython)
    handler = get_display_handler()

    mock_display_handle = Mock()
    mock_display = Mock(return_value=mock_display_handle)
    monkeypatch.setattr("IPython.display.display", mock_display)

    trace_a = create_trace("a")
    trace_b = create_trace("b")
    trace_c = create_trace("c")

    # The display client should dedupe traces to display and only display 3 (not 6).
    handler.display_traces([trace_a])
    handler.display_traces([trace_b])
    handler.display_traces([trace_c])
    handler.display_traces([trace_a, trace_b, trace_c])

    expected = [trace_a, trace_b, trace_c]

    assert mock_display.call_count == 1
    assert mock_display_handle.update.call_count == 3
    assert mock_display_handle.update.call_args[0][0] == {
        "application/databricks.mlflow.trace": json.dumps(
            [json.loads(t.to_json()) for t in expected]
        ),
        "text/plain": expected.__repr__(),
    }
