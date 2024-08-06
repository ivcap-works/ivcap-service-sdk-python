#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#

# read version from installed package


try:  # Python < 3.10 (backport)
    from importlib_metadata import version
except ImportError:
    from importlib.metadata import version

try:
    __version__ = version("ivcap_sdk_service")
except Exception:
    __version__ = "unknown"


from .ivcap import publish_artifact, fetch_data, register_saver
from .ivcap import create_aspect, publish_aspect, find_aspect, publish_file_as_artifact
from .ivcap import create_metadata
from .ivcap import SCHEMA_KEY, publish_result
from .ivcap import get_config, register_saver, get_order_id, get_node_id
from .ivcap import QueueService, get_queue_service
from .run import register_service
from .service import Service, Parameter, Option, Type
from .service import Workflow, BasicWorkflow, PythonWorkflow
from .aspect import Aspect, GenericAspect

from .cio.io_adapter import IOAdapter, IOWritable, IOReadable, QueueMessage
from .cio.io_adapter import ASPECT_MSG_SCHEMA, END_OF_STREAM_SCHEMA
from .cio.io_adapter import OnCloseF, Queue
from .itypes import MissingParameterValue, UnsupportedMimeType, SupportedMimeTypes, ServiceArgs
from .itypes import MetaDict, URN, Url, AspectDict
