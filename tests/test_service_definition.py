#
# Copyright (c) 2026 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
import json

import pytest
from pydantic import BaseModel, Field

from ivcap_service.service import Service, ServiceContact, ServiceLicense
from ivcap_service.service_definition import (
    BATCH_CONTROLLER_SCHEMA,
    DEF_POLICY,
    SERVICE_SCHEMA,
    BatchController,
    ResourceRequirements,
    Resources,
    ServiceDefinition,
    create_batch_service_definition,
    create_service_definition,
    extract_line,
    find_command,
    find_resources_file,
)
from ivcap_service.tool_definition import SERVICE_ID_PLACEHOLDER


class EchoRequest(BaseModel):
    msg: str = Field(description="message to echo")


class EchoResult(BaseModel):
    msg: str = Field(description="echoed message")


def echo(req: EchoRequest) -> EchoResult:
    """Echoes the given message back."""
    return EchoResult(msg=req.msg)


@pytest.fixture
def service_description() -> Service:
    return Service(
        name="Echo Service",
        version="1.2.3",
        contact=ServiceContact(name="Jane Doe", email="jane@example.com"),
        license=ServiceLicense(name="MIT", url="https://opensource.org/license/MIT"),
    )


def test_resource_requirements_defaults():
    rr = ResourceRequirements()
    assert rr.cpu == "500m"
    assert rr.memory == "1Gi"
    assert rr.ephemeral_storage is None


def test_resources_defaults():
    resources = Resources()
    assert resources.limits.cpu == "500m"
    assert resources.requests.memory == "1Gi"


def test_batch_controller_schema_default():
    controller = BatchController(image="my-image:latest", command=["python", "app.py"])
    assert controller.jschema == BATCH_CONTROLLER_SCHEMA
    assert controller.image == "my-image:latest"
    assert controller.command == ["python", "app.py"]


def test_create_service_definition_basic(service_description, monkeypatch):
    monkeypatch.delenv("IVCAP_SERVICE_NAME", raising=False)
    monkeypatch.delenv("IVCAP_SERVICE_ID", raising=False)
    monkeypatch.delenv("IVCAP_POLICY_URN", raising=False)

    controller = BatchController(image="my-image:latest", command=["python", "app.py"])
    sd = create_service_definition(
        service_description, echo, BATCH_CONTROLLER_SCHEMA, controller
    )

    assert isinstance(sd, ServiceDefinition)
    assert sd.jschema == SERVICE_SCHEMA
    assert sd.id == SERVICE_ID_PLACEHOLDER
    assert sd.name == "Echo Service"
    assert sd.description == "Echoes the given message back."
    assert sd.policy == DEF_POLICY
    assert sd.contact.name == "Jane Doe"
    assert sd.license is not None
    assert sd.license.name == "MIT"
    assert sd.controller_schema == BATCH_CONTROLLER_SCHEMA
    assert sd.request_schema is not None
    assert sd.request_schema["properties"]["msg"]["description"] == "message to echo"
    assert sd.result_schema is not None
    assert sd.result_schema["properties"]["msg"]["description"] == "echoed message"


def test_create_service_definition_uses_env_overrides(service_description, monkeypatch):
    monkeypatch.setenv("IVCAP_SERVICE_NAME", "env-echo")
    monkeypatch.setenv("IVCAP_SERVICE_ID", "urn:ivcap:service:from-env")
    monkeypatch.setenv("IVCAP_POLICY_URN", "urn:ivcap:policy:custom")

    controller = BatchController(image="my-image:latest", command=["python", "app.py"])
    sd = create_service_definition(
        service_description, echo, BATCH_CONTROLLER_SCHEMA, controller
    )

    assert sd.name == "env-echo"
    assert sd.id == "urn:ivcap:service:from-env"
    assert sd.policy == "urn:ivcap:policy:custom"


def test_create_service_definition_explicit_service_id(service_description):
    controller = BatchController(image="my-image:latest", command=["python", "app.py"])
    sd = create_service_definition(
        service_description,
        echo,
        BATCH_CONTROLLER_SCHEMA,
        controller,
        service_id="urn:ivcap:service:explicit",
    )
    assert sd.id == "urn:ivcap:service:explicit"


def test_service_definition_serialization_uses_aliases(service_description):
    controller = BatchController(image="my-image:latest", command=["python", "app.py"])
    sd = create_service_definition(
        service_description, echo, BATCH_CONTROLLER_SCHEMA, controller
    )
    dumped = sd.model_dump(by_alias=True, exclude_none=True)

    assert dumped["$schema"] == SERVICE_SCHEMA
    assert dumped["$id"] == SERVICE_ID_PLACEHOLDER
    assert dumped["controller-schema"] == BATCH_CONTROLLER_SCHEMA
    assert dumped["request-schema"]["properties"]["msg"]["description"] == (
        "message to echo"
    )
    assert "controller_schema" not in dumped
    assert "request_schema" not in dumped


def test_find_resources_file_defaults_when_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("IVCAP_RESOURCES_FILE", raising=False)

    resources = find_resources_file()

    assert resources.limits.cpu == "500m"
    assert resources.requests.memory == "1Gi"


def test_find_resources_file_reads_custom_file(tmp_path, monkeypatch):
    resource_file = tmp_path / "custom-resources.json"
    resource_file.write_text(
        json.dumps(
            {
                "limits": {"cpu": "2", "memory": "4Gi"},
                "requests": {"cpu": "1", "memory": "2Gi"},
            }
        )
    )
    monkeypatch.setenv("IVCAP_RESOURCES_FILE", str(resource_file))

    resources = find_resources_file()

    assert resources.limits.cpu == "2"
    assert resources.limits.memory == "4Gi"
    assert resources.requests.cpu == "1"


def test_find_resources_file_exits_when_explicit_file_missing(tmp_path, monkeypatch):
    missing_file = tmp_path / "does-not-exist.json"
    monkeypatch.setenv("IVCAP_RESOURCES_FILE", str(missing_file))

    with pytest.raises(SystemExit):
        find_resources_file()


def test_find_command_from_entrypoint_env_list(monkeypatch):
    monkeypatch.setenv("ENTRYPOINT", '["python", "app.py"]')
    cmd = find_command()
    assert cmd == ["python", "app.py"]


def test_find_command_from_entrypoint_env_non_list(monkeypatch):
    monkeypatch.setenv("ENTRYPOINT", "not-a-list-literal")
    cmd = find_command()
    assert cmd == ["not-a-list-literal"]


def test_find_command_missing_dockerfile(tmp_path, monkeypatch):
    monkeypatch.delenv("ENTRYPOINT", raising=False)
    monkeypatch.chdir(tmp_path)

    cmd = find_command()

    assert cmd == ["#ENTRYPOINT#"]


def test_find_command_from_dockerfile(tmp_path, monkeypatch):
    monkeypatch.delenv("ENTRYPOINT", raising=False)
    monkeypatch.chdir(tmp_path)
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text(
        'FROM python:3.11-slim\nWORKDIR /app\nENTRYPOINT ["python", "app.py"]\n'
    )

    cmd = find_command()

    assert cmd == ["python", "app.py"]


def test_find_command_dockerfile_without_entrypoint(tmp_path, monkeypatch):
    monkeypatch.delenv("ENTRYPOINT", raising=False)
    monkeypatch.chdir(tmp_path)
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM python:3.11-slim\nWORKDIR /app\n")

    cmd = find_command()

    assert cmd == ["#ENTRYPOINT#"]


def test_extract_line_finds_matching_line(tmp_path):
    file_path = tmp_path / "Dockerfile"
    file_path.write_text('FROM python:3.11\nENTRYPOINT ["python", "app.py"]\n')

    line = extract_line(str(file_path), "ENTRYPOINT")

    assert line == 'ENTRYPOINT ["python", "app.py"]'


def test_extract_line_returns_none_when_not_found(tmp_path):
    file_path = tmp_path / "Dockerfile"
    file_path.write_text("FROM python:3.11\n")

    line = extract_line(str(file_path), "ENTRYPOINT")

    assert line is None


def test_create_batch_service_definition(service_description, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ENTRYPOINT", raising=False)
    monkeypatch.delenv("IVCAP_RESOURCES_FILE", raising=False)
    monkeypatch.setenv("DOCKER_IMG", "my-registry/echo:1.0.0")
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text(
        'FROM python:3.11-slim\nENTRYPOINT ["python", "batch_service.py"]\n'
    )

    sd = create_batch_service_definition(service_description, echo)

    assert sd.controller_schema == BATCH_CONTROLLER_SCHEMA
    assert sd.controller.image == "my-registry/echo:1.0.0"
    assert sd.controller.command == ["python", "batch_service.py"]
    # No custom resources file present => falls back to defaults.
    assert sd.controller.resources.limits.cpu == "500m"
