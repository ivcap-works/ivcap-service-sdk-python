#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
from typing import Dict
from PIL import Image

from ivcap_sdk_service import Service, Parameter, Type, register_service
import logging

SERVICE = Service(
    name = "load-artifact",
    description = "Service to test loading an artifacts",
    providerID = "ivcap:provider:0000-0000-0000",
    parameters = [
        Parameter(name="load", type=Type.ARTIFACT, description="Artifact to load"),
   ]
)

def load_artifact(args: Dict, logger: logging):
    logger.info(f"Called with {args}")
    img = Image.open(args.load)
    [width, height] = img.size
    logger.info(f"Image dimensions: {width}x{height}")

register_service(SERVICE, load_artifact)