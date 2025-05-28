#
# Copyright (c) 2025 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
""" A library for building services for the IVCAP platform"""

from .version import __version__
from .logger import getLogger, logging_init, service_log_config, set_service_log_config
from .service import start_batch_service, Service
from .service_definition import create_service_definition, find_resources_file, find_command, IMAGE_PLACEHOLDER, Resources, ServiceDefinition
from .tool_definition import create_tool_definition, print_tool_definition, ToolDefinition
from .utils import get_function_return_type, get_input_type
from .ivcap import get_ivcap_url, verify_result, push_result
from .types import IvcapResult, BinaryResult, ExecutionError, JobContext
from .context import otel_instrument, set_context
from .events import EventReporter