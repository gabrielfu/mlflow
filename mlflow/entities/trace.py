from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from mlflow.entities._mlflow_object import _MlflowObject
from mlflow.entities.trace_data import TraceData
from mlflow.entities.trace_info import TraceInfo
from mlflow.tracing.utils import TraceJSONEncoder


@dataclass
class Trace(_MlflowObject):
    """A trace object. (TODO: Add conceptual guide for tracing.)

    Args:
        info: A lightweight object that contains the metadata of a trace.
        data: A container object that holds the spans data of a trace.
    """

    info: TraceInfo
    data: TraceData

    def to_json(self) -> str:
        return json.dumps(
            {"info": asdict(self.info), "data": self.data.to_dict()}, cls=TraceJSONEncoder
        )

    def _repr_mimebundle_(self, include=None, exclude=None):
        """
        This method is used to trigger custom display logic in IPython notebooks.
        See https://ipython.readthedocs.io/en/stable/config/integrating.html#MyObject
        for more details.

        At the moment, the only supported MIME type is "application/databricks.mlflow.trace",
        which contains a JSON representation of the Trace object. This object is deserialized
        in Databricks notebooks to display the Trace object in a nicer UI.
        """
        return {
            "application/databricks.mlflow.trace": self.to_json(),
            "text/plain": self.__repr__(),
        }
