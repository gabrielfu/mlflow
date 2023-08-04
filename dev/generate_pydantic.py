import os
from functools import partial
from typing import List, Type, Optional, Union
from enum import IntEnum

from google.protobuf.reflection import GeneratedProtocolMessageType
from google.protobuf.descriptor import DescriptorBase, Descriptor, FieldDescriptor, EnumDescriptor
from google.protobuf.struct_pb2 import Struct
from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf.duration_pb2 import Duration
from pydantic import BaseModel, Field
from fastapi import Query, Body
from typing_extensions import Annotated

type_mapping = {
    FieldDescriptor.TYPE_DOUBLE: float,
    FieldDescriptor.TYPE_FLOAT: float,
    FieldDescriptor.TYPE_INT64: int,
    FieldDescriptor.TYPE_UINT64: int,
    FieldDescriptor.TYPE_INT32: int,
    FieldDescriptor.TYPE_FIXED64: float,
    FieldDescriptor.TYPE_FIXED32: float,
    FieldDescriptor.TYPE_BOOL: bool,
    FieldDescriptor.TYPE_STRING: str,
    FieldDescriptor.TYPE_BYTES: str,
    FieldDescriptor.TYPE_UINT32: int,
    FieldDescriptor.TYPE_SFIXED32: float,
    FieldDescriptor.TYPE_SFIXED64: float,
    FieldDescriptor.TYPE_SINT32: int,
    FieldDescriptor.TYPE_SINT64: int,
}


"""
message GetExperimentByName {
  option (scalapb.message).extends = "com.databricks.rpc.RPC[$this.Response]";

  // Name of the associated experiment.
  optional string experiment_name = 1 [(validate_required) = true];

  message Response {
    // Experiment details.
    optional Experiment experiment = 1;
  }
}

->
type(GetExperimentByName)
Out[3]: google.protobuf.pyext.cpp_message.GeneratedProtocolMessageType

type(GetExperimentByName.DESCRIPTOR)
Out[4]: google.protobuf.pyext._message.MessageDescriptor

type(GetExperimentByName.experiment_name)
Out[10]: google.protobuf.pyext._message.FieldProperty

type(GetExperimentByName.experiment_name.DESCRIPTOR)
Out[11]: google.protobuf.pyext._message.FieldDescriptor

type(GetExperimentByName.Response)
Out[12]: google.protobuf.pyext.cpp_message.GeneratedProtocolMessageType

type(GetExperimentByName.Response.DESCRIPTOR)
Out[13]: google.protobuf.pyext._message.MessageDescriptor
"""


def _is_required(field: FieldDescriptor):
    if field.label == FieldDescriptor.LABEL_REQUIRED:
        return True
    for key, value in field.GetOptions().ListFields():
        if key.name == "validate_required" and value is True:
            return True
    return False


def _compile_field(
        field: FieldDescriptor,
        is_query: bool,
):
    if field.type == FieldDescriptor.TYPE_ENUM:
        enum_type: EnumDescriptor = field.enum_type
        type_statement = "..."
        default = ""
    elif field.type == FieldDescriptor.TYPE_MESSAGE:
        type_statement = "..."
        default = ""
    else:
        type_statement = type_mapping[field.type].__name__
        default = type_statement + "()"

    if field.label == FieldDescriptor.LABEL_REPEATED:
        type_statement = f"List[{type_statement}]"
        default = "[]"

    if _is_required(field):
        default = ""
    else:
        type_statement = f"Optional[{type_statement}]"

    if is_query:
        default_statement = f" = Field(Query({default}))"
    else:
        default_statement = ""

    field_statement = f"{field.name}: {type_statement}{default_statement}"
    print(field_statement)


def _compile_descriptor(descriptor: Descriptor):
    name = descriptor.name


"""
======================================================================
SearchExperiments:

class SearchExperimentsModel99096dcc(BaseModel):
    max_results: Optional[int] = Field(Query(None))
    page_token: Optional[str] = Field(Query(None))
    filter: Optional[str] = Field(Query(None))
    order_by: Optional[List[str]] = Field(Query(None))

    class ViewType(IntEnum):
        ACTIVE_ONLY = 1
        DELETED_ONLY = 2
        ALL = 3

    view_type: Optional[ViewType] = Field(Query(None))
def getter(): return SearchExperimentsModel99096dcc
======================================================================
SearchExperiments.Response:

class ResponseModel7acfaa71(BaseModel):

    class Experiment(BaseModel):
        experiment_id: Optional[str] = Field(Query(None))
        name: Optional[str] = Field(Query(None))
        artifact_location: Optional[str] = Field(Query(None))
        lifecycle_stage: Optional[str] = Field(Query(None))
        last_update_time: Optional[int] = Field(Query(None))
        creation_time: Optional[int] = Field(Query(None))

        class ExperimentTag(BaseModel):
            key: Optional[str] = Field(Query(None))
            value: Optional[str] = Field(Query(None))

        tags: Optional[List[ExperimentTag]] = Field(Query(None))

    experiments: Optional[List[Experiment]] = Field(Query(None))
    next_page_token: Optional[str] = Field(Query(None))
def getter(): return ResponseModel7acfaa71
======================================================================
"""


from mlflow.protos.service_pb2 import SearchExperiments
_compile_field(SearchExperiments.page_token.DESCRIPTOR, True)
