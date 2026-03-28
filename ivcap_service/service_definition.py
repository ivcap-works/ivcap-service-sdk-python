#
# Copyright (c) 2025 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#

import ast
import os
import sys
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from .logger import getLogger
from .service import Service, ServiceContact, ServiceLicense
from .tool_definition import SERVICE_ID_PLACEHOLDER
from .utils import clean_description, file_to_json

SERVICE_SCHEMA = "urn:ivcap:schema.service.2"
BATCH_CONTROLLER_SCHEMA = "urn:ivcap:schema.service.batch.1"
DEF_POLICY = "urn:ivcap:policy:ivcap.open.service"
DEF_RESOURCE_FILE = "resources.json"

IMAGE_PLACEHOLDER = "#DOCKER_IMG#"

logger = getLogger("service-defintion")


class ResourceRequirements(BaseModel):
    cpu: str = Field(default="500m")
    memory: str = Field(default="1Gi")
    ephemeral_storage: str | None = None  # Field(default="1Gi")


class Resources(BaseModel):
    limits: ResourceRequirements = Field(default_factory=ResourceRequirements)
    requests: ResourceRequirements = Field(default_factory=ResourceRequirements)


class BatchController(BaseModel):
    jschema: str = Field(default=BATCH_CONTROLLER_SCHEMA, alias="$schema")
    image: str
    command: list[str] | str
    resources: Resources = Field(default_factory=Resources)


class ServiceDefinition(BaseModel):
    jschema: str = Field(default=SERVICE_SCHEMA, alias="$schema")
    id: str = Field(alias="$id")
    name: str
    description: str
    parameters: list[Any] = []
    contact: ServiceContact = Field(description="contact details of the service")
    license: ServiceLicense | None = Field(
        None, description="license details of the service"
    )
    policy: str = Field(default=DEF_POLICY)
    controller_schema: str = Field(
        description="URN identifying the controller for this service",
        alias="controller-schema",
    )
    controller: Any

    model_config = {
        "populate_by_name": True,
    }


def print_batch_service_definition(
    service_description: Service,
    fn: Callable[..., Any],
    service_id: str | None = None,
):
    sd = create_batch_service_definition(
        service_description,
        fn,
        service_id=service_id,
    )
    print(sd.model_dump_json(indent=2, by_alias=True, exclude_none=True))


def create_batch_service_definition(
    service_description: Service,
    fn: Callable[..., Any],
    service_id: str | None = None,
) -> ServiceDefinition:
    # controller
    image = os.getenv("DOCKER_IMG", IMAGE_PLACEHOLDER)

    command = find_command()
    resources = find_resources_file()
    controller = BatchController(image=image, command=command, resources=resources)
    return create_service_definition(
        service_description, fn, BATCH_CONTROLLER_SCHEMA, controller, service_id
    )


def create_service_definition(
    service_description: Service,
    fn: Callable[..., Any],
    controller_schema: str,
    controller: Any,
    service_id: str | None = None,
    description: str | None = None,
) -> ServiceDefinition:
    name = os.getenv("IVCAP_SERVICE_NAME", service_description.name)
    if service_id is None:
        service_id = os.getenv("IVCAP_SERVICE_ID", SERVICE_ID_PLACEHOLDER)
    description = clean_description(fn.__doc__ or "no description available")
    contact = service_description.contact
    license = service_description.license
    policy = os.getenv("IVCAP_POLICY_URN", DEF_POLICY)

    sd_data = {
        "$id": service_id,
        "name": name,
        "description": description,
        "policy": policy,
        "contact": contact,
        "license": license,
        "controller_schema": controller_schema,
        "controller": controller,
    }

    sd = ServiceDefinition(**sd_data)
    return sd


def find_resources_file() -> Resources:
    using_def_resource_file = False
    resource_file = os.getenv("IVCAP_RESOURCES_FILE")
    if resource_file is None:
        using_def_resource_file = True
        resource_file = DEF_RESOURCE_FILE

    if os.path.exists(resource_file) and os.access(resource_file, os.R_OK):
        rd = file_to_json(resource_file)
        resources = Resources(**rd)
    else:
        if using_def_resource_file:
            # should not use logger as this is likely piped into some other command
            print(
                f"WARNING: Using default resources as I can't find resources def '{resource_file}'",
                file=sys.stderr,
            )
            resources = Resources()
        else:
            print(
                f"FATAL: Cannot open resources definition file '{resource_file}'",
                file=sys.stderr,
            )
            sys.exit(-1)
    return resources


def find_command() -> list[str]:
    docker_file = os.getenv("DOCKERFILE", "Dockerfile")
    if not (os.path.exists(docker_file) and os.access(docker_file, os.R_OK)):
        print(f"FATAL: Cannot find Dockerfile '{docker_file}'", file=sys.stderr)
        sys.exit(-1)

    entry = extract_line(docker_file, "ENTRYPOINT")
    if not entry:
        print(f"FATAL: Cannot find 'ENTRYPOINT' in '{docker_file}'", file=sys.stderr)
        sys.exit(-1)
    cs = entry[len("ENTRYPOINT") :].strip()
    cmd = ast.literal_eval(cs)
    return cmd


def extract_line(filepath, start_string):
    with open(filepath) as f:
        for line in f:
            if line.startswith(start_string):
                return line.strip()
    return None
