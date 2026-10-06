#
# Copyright (c) 2026 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
import pytest
from pydantic import BaseModel, Field

from ivcap_service.tool_definition import (
    SERVICE_ID_PLACEHOLDER,
    TOOL_SCHEMA,
    ToolDefinition,
    _generate_function_description,
    create_tool_definition,
)
from ivcap_service.types import ExecutionContext


class GreetRequest(BaseModel):
    """Request for the greeting tool."""

    name: str = Field(description="name of the person to greet")
    excited: bool | None = Field(False, description="whether to add an exclamation mark")
    tags: list[str] | None = Field(None, description="optional tags")


class GreetResult(BaseModel):
    message: str = Field(description="the greeting message")


def greet(req: GreetRequest) -> GreetResult:
    """Greets a person by name.

    Returns a friendly greeting.
    """
    return GreetResult(message=f"Hello, {req.name}")


def greet_with_context(req: GreetRequest, ctxt: ExecutionContext) -> GreetResult:
    """Greets a person by name, with an execution context."""
    return GreetResult(message=f"Hello, {req.name}")


def no_model_fn(a: str, b: int) -> str:
    """A function without any Pydantic model argument."""
    return f"{a}{b}"


def test_create_tool_definition_basic(monkeypatch):
    monkeypatch.delenv("IVCAP_SERVICE_NAME", raising=False)
    monkeypatch.delenv("IVCAP_SERVICE_ID", raising=False)

    td = create_tool_definition(greet)

    assert isinstance(td, ToolDefinition)
    assert td.jschema == TOOL_SCHEMA
    assert td.name == "greet"
    assert td.id == "urn:sd-core:ai-tool.greet"
    assert td.service_id == SERVICE_ID_PLACEHOLDER
    assert "Greets a person by name" in td.description
    assert td.fn_schema["properties"]["name"]["description"] == (
        "name of the person to greet"
    )


def test_create_tool_definition_custom_name_and_service_id():
    td = create_tool_definition(
        greet,
        name="My Greeter",
        service_id="urn:ivcap:service:1234",
        id_prefix="urn:sd-core:ai-tool",
    )

    # Spaces and dashes are normalised and lower-cased.
    assert td.name == "my_greeter"
    assert td.service_id == "urn:ivcap:service:1234"
    assert td.id == "urn:sd-core:ai-tool.my_greeter"


def test_create_tool_definition_uses_env_vars(monkeypatch):
    monkeypatch.setenv("IVCAP_SERVICE_NAME", "env-name")
    monkeypatch.setenv("IVCAP_SERVICE_ID", "urn:ivcap:service:from-env")

    td = create_tool_definition(greet)

    assert td.name == "env_name"
    assert td.service_id == "urn:ivcap:service:from-env"


def test_create_tool_definition_no_pydantic_model_raises():
    with pytest.raises(ValueError, match="no Pydantic input model"):
        create_tool_definition(no_model_fn)


def test_create_tool_definition_excludes_execution_context():
    td = create_tool_definition(greet_with_context)

    # ExecutionContext parameter must not leak into the generated signature.
    assert "ctxt" not in td.fn_signature
    assert "name" in td.fn_signature


def test_tool_definition_serialization_uses_aliases():
    td = create_tool_definition(greet, service_id="urn:ivcap:service:abc")
    dumped = td.model_dump(by_alias=True)

    assert dumped["$schema"] == TOOL_SCHEMA
    assert dumped["service-id"] == "urn:ivcap:service:abc"
    assert "jschema" not in dumped
    assert "service_id" not in dumped


def test_generate_function_description_no_model():
    signature, description = _generate_function_description(no_model_fn)
    assert signature == ""
    assert "does not have a Pydantic model" in description


def test_generate_function_description_includes_fields_and_return():
    signature, description = _generate_function_description(greet, name="greet")

    assert signature.startswith("greet(")
    assert "name: str" in signature
    assert "Returns: GreetResult" in description
    assert "name of the person to greet" in description


def test_generate_function_description_optional_field_defaults():
    _signature, description = _generate_function_description(greet, name="greet")

    # `excited` is a `bool | None` field with a default - description should
    # mention the resolved annotation type and the default value.
    assert "excited: bool | None" in description
    assert "Defaults to False" in description


def test_generate_function_description_array_field():
    _signature, description = _generate_function_description(greet, name="greet")

    assert "tags: list[str] | None" in description
    assert "Defaults to None" in description


def test_generate_function_description_excludes_type():
    _signature, description = _generate_function_description(
        greet_with_context, exclude_types=[ExecutionContext]
    )

    assert "ctxt" not in description
