"""
Modified from
https://github.com/Ed-XCF/protobuf2pydantic

Reference only
"""

import uuid
from os import linesep
from functools import partial
from typing import List, Type, Optional  # noqa
from enum import IntEnum  # noqa

from google.protobuf.reflection import GeneratedProtocolMessageType
from google.protobuf.descriptor import Descriptor, FieldDescriptor, EnumDescriptor
from google.protobuf.struct_pb2 import Struct  # noqa
from google.protobuf.timestamp_pb2 import Timestamp  # noqa
from google.protobuf.duration_pb2 import Duration  # noqa
from pydantic import BaseModel, Field  # noqa
from fastapi import Query, Body  # noqa
from typing_extensions import Annotated

message_metaclasses = [GeneratedProtocolMessageType]
try:
    from google._upb._message import MessageMeta

    message_metaclasses.append(MessageMeta)
except ImportError:
    pass

tab = " " * 4
one_line, two_lines = linesep * 2, linesep * 3
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


def m(field: FieldDescriptor) -> str:
    return type_mapping[field.type].__name__


def _is_required(field: FieldDescriptor):
    if field.label == FieldDescriptor.LABEL_REQUIRED:
        return True
    for key, value in field.GetOptions().ListFields():
        if key.name == "validate_required" and value is True:
            return True
    return False


def convert_field(level: int, is_query: bool, field: FieldDescriptor) -> str:
    level += 1
    field_type = field.type
    field_label = field.label
    was_mapping = False
    extra = None
    name = field.name

    if field_type == FieldDescriptor.TYPE_ENUM:
        enum_type: EnumDescriptor = field.enum_type
        type_statement = enum_type.name
        class_statement = f"{tab * level}class {enum_type.name}(IntEnum):"
        field_statements = map(
            lambda v: f"{tab * (level + 1)}{v.name} = {v.index}",
            enum_type.values,
        )
        extra = linesep.join([class_statement, *field_statements])
        factory = "int"

    elif field_type == FieldDescriptor.TYPE_MESSAGE:
        type_statement: str = field.message_type.name
        if type_statement.endswith("Entry"):
            key, value = field.message_type.fields  # type: FieldDescriptor
            if value.type != 11:
                type_statement = f"Dict[{m(key)}, {m(value)}]"
            else:
                was_mapping = True
                type_statement = f"Dict[{m(key)}, {value.message_type.name}]"
            factory = "dict"
        elif type_statement == "Struct":
            type_statement = "Dict[str, Any]"
            factory = "dict"
        else:
            extra = _descriptor2pydantic(level, field.message_type, is_query=is_query)
            factory = type_statement
    else:
        type_statement = m(field)
        factory = type_statement

    if field_label == FieldDescriptor.LABEL_REPEATED and not was_mapping:
        type_statement = f"List[{type_statement}]"
        factory = "list"

    if _is_required(field):
        default_value = ""
    else:
        default_value = "None"
        type_statement = f"Optional[{type_statement}]"

    if is_query:
        default_statement = f" = Field(Query({default_value}))"
    else:
        default_statement = ""

    field_statement = f"{tab * level}{field.name}: {type_statement}{default_statement}"
    if not extra:
        return field_statement
    return linesep + extra + one_line + field_statement


def _descriptor2pydantic(
        level: int,
        descriptor: Descriptor,
        model_name: str = None,
        is_query: bool = True,
) -> str:
    model_name = model_name or descriptor.name
    class_statement = f"{tab * level}class {model_name}(BaseModel):"
    field_statements = map(partial(convert_field, level, is_query), descriptor.fields)
    return linesep.join([class_statement, *field_statements])


def message2pydantic(
        message: GeneratedProtocolMessageType,
        is_query: bool = True,
) -> Type[BaseModel]:
    """ convert a protobuf message object to pydantic model object """
    descriptor = message.DESCRIPTOR
    # Unique model name for each call
    rand = str(uuid.uuid4())[:8]
    model_name = f"{descriptor.name}Model{rand}"
    model_string = _descriptor2pydantic(0, descriptor, model_name, is_query)
    getter_key = "getter"
    getter_string = f"def {getter_key}(): return {model_name}"
    compile_string = model_string + linesep + getter_string
    compile_code = compile(compile_string, "<string>", "exec")
    sub_namespace = {k: v for k, v in globals().items() if not k.startswith("__")}
    exec(compile_code, sub_namespace)
    return sub_namespace[getter_key]()


def make_body_parameter_type(message: GeneratedProtocolMessageType):
    return Annotated[message2pydantic(message, is_query=False), Body()]

