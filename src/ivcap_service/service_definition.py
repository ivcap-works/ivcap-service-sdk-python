#
# Copyright (c) 2025 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#

import os
import sys
from typing import Callable, Dict, List, Any, Optional
from pydantic import BaseModel, Field

from .utils import file_to_json
from .tool_definition import SERVICE_ID_PLACEHOLDER
from .logger import getLogger

SERVICE_SCHEMA = "urn:ivcap:schema.service.2"
BATCH_CONTROLLER_SCHEMA = "urn:ivcap:schema.service.batch.1"
DEF_POLICY = "urn:ivcap:policy:ivcap.open.service"
DEF_RESOURCE_FILE = "resources.json"

IMAGE_PLACEHOLDER = "#DOCKER_IMG#"

logger = getLogger("service-defintion")

class ResourceRequirements(BaseModel):
    cpu: str = Field(default="500m")
    memory: str = Field(default="1Gi")
    ephemeral_storage: Optional[str] = None # Field(default="1Gi")

class Resources(BaseModel):
    limits: ResourceRequirements = Field(default_factory=ResourceRequirements)
    requests: ResourceRequirements = Field(default_factory=ResourceRequirements)

class BatchController(BaseModel):
    jschema: str = Field(default=BATCH_CONTROLLER_SCHEMA, alias="$schema")
    image: str
    command: List[str]
    resources: Resources = Field(default_factory=Resources)

class ServiceDefinition(BaseModel):
    jschema: str = Field(default=SERVICE_SCHEMA, alias="$schema")
    id: str = Field(alias="$id")
    name: str
    description: str
    parameters: List[Any] = []
    policy: str = Field(default=DEF_POLICY)
    controller_schema: str = Field(default=BATCH_CONTROLLER_SCHEMA)
    controller: Any

def print_batch_service_definition(
    fn: Callable[..., Any],
    service_id: Optional[str] = None,
    description: Optional[str] = None,
):
    sd = create_batch_service_definition(
        fn,
        service_id=service_id,
        description=description,
    )
    print(sd.model_dump_json(indent=2, by_alias=True, exclude_none=True))

def create_batch_service_definition(
    fn: Callable[..., Any],
    service_id: Optional[str] = None,
    description: Optional[str] = None,
) -> ServiceDefinition:
    # controller
    image = os.getenv("DOCKER_IMG", IMAGE_PLACEHOLDER)
    service_file_name = fn.__code__.co_filename
    service_dir = os.path.dirname(service_file_name)
    service_file_name = os.path.basename(service_file_name)
    command = ["python", f"/app/{service_file_name}"]

    using_def_resource_file = False
    resource_file = os.getenv("IVCAP_RESOURCES_FILE")
    if resource_file == None:
        using_def_resource_file = True
        resource_file = os.path.join(service_dir, DEF_RESOURCE_FILE)
    if os.path.exists(resource_file) and os.access(resource_file, os.R_OK):
        rd = file_to_json(resource_file)
        resources = Resources(**rd)
    else:
        if using_def_resource_file:
            logger.info(f"Using default resources as I can't find resources def '{resource_file}'")
            resources = Resources()
        else:
            logger.warning(f"Cannot open resources definition file '{resource_file}'")
            sys.exit(-1)

    controller = BatchController(image=image, command=command, resources=resources)
    return create_service_definition(fn, controller, service_id, description)

def create_service_definition(
    fn: Callable[..., Any],
    controller: Any,
    service_id: Optional[str] = None,
    description: Optional[str] = None,
) -> ServiceDefinition:
    name = os.getenv("IVCAP_SERVICE_NAME", fn.__name__)
    if service_id == None:
        service_id = os.getenv("IVCAP_SERVICE_ID", SERVICE_ID_PLACEHOLDER)
    if description == None:
        description = fn.__doc__ or "no description available"
    policy = os.getenv("IVCAP_POLICY_URN", DEF_POLICY)


    sd_data = {
        "$id": service_id,
        "name": name,
        "description": description,
        "policy": policy,
        "controller": controller,
    }

    sd = ServiceDefinition(**sd_data)
    return sd
