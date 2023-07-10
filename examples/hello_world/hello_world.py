#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
from typing import Dict
from ivcap_sdk_service import Service, Parameter, PythonWorkflow, Type, register_service
import logging

SERVICE = Service(
    name = "HelloWorld",
    description = "Simple service which does a few simple things",
    parameters = [
        Parameter(name="msg", type=Type.STRING, description="Message to echo"),
        Parameter(name="times", type=Type.INT, default=2, description="Times to repeat"),
    ],
    workflow = PythonWorkflow(min_memory='2Gi')
)

def hello_world(args: Dict, logger: logging):
    for i in range(args.times):
        logger.info(f"({i + 1}) Hello {args.msg}")

register_service(SERVICE, hello_world)