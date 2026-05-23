#
# Copyright (c) 2025 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
"""A library for building services for the IVCAP platform"""

from .context import otel_instrument, set_context
from .events import (
    BaseEvent,
    EventFactoryF,
    EventReporter,
    GenericErrorEvent,
    GenericEvent,
    create_event_reporter,
    set_event_reporter_factory,
)
from .ivcap import (
    OnResultF,
    SidecarReporter,
    get_ivcap_url,
    push_result,
    set_result_callback,
    verify_result,
)
from .logger import getLogger, logging_init, service_log_config, set_service_log_config
from .openobserve import init_openobserve_from_env, load_openobserve_config_from_env
from .secret import get_secret
from .service import Service, start_batch_service
from .service_definition import (
    IMAGE_PLACEHOLDER,
    Resources,
    ServiceDefinition,
    create_service_definition,
    find_command,
    find_resources_file,
)
from .tool_definition import (
    ToolDefinition,
    create_tool_definition,
    print_tool_definition,
)
from .types import BinaryResult, ExecutionError, IvcapResult, JobContext
from .utils import get_function_return_type, get_input_type
from .version import __version__, get_version

__all__ = [
    "BaseEvent",
    "BinaryResult",
    "EventFactoryF",
    "EventReporter",
    "ExecutionError",
    "GenericErrorEvent",
    "GenericEvent",
    "IMAGE_PLACEHOLDER",
    "IvcapResult",
    "JobContext",
    "OnResultF",
    "Resources",
    "Service",
    "ServiceDefinition",
    "SidecarReporter",
    "ToolDefinition",
    "__version__",
    "create_event_reporter",
    "create_service_definition",
    "create_tool_definition",
    "find_command",
    "find_resources_file",
    "getLogger",
    "get_function_return_type",
    "get_input_type",
    "get_ivcap_url",
    "get_secret",
    "get_version",
    "logging_init",
    "otel_instrument",
    "print_tool_definition",
    "push_result",
    "service_log_config",
    "set_context",
    "set_event_reporter_factory",
    "set_result_callback",
    "set_service_log_config",
    "start_batch_service",
    "init_openobserve_from_env",
    "load_openobserve_config_from_env",
    "verify_result",
]
