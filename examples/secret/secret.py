#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
import logging

from ivcap_sdk_service import (
    Service,
    Parameter,
    Type,
    ServiceArgs,
    PythonWorkflow,
    register_service,
    get_secret,
)

SERVICE = Service(
    name="TaskSecret",
    description="A simple demo service for read secert",
    parameters = [
        Parameter(name="secret-name", type=Type.STRING, description="Secret name to read"),
    ],
    workflow=PythonWorkflow(
        min_memory="2Gi", min_cpu="500m", min_ephemeral_storage="4Gi"
    ),
)

def get_secret_service(args: ServiceArgs, logger: logging):
    """
    Main function to create tasks and add them to the queue.
    """
    value = get_secret(args.secret_name)
    # ALERT, don't log it in prod, its only for demo purpose
    logger.info(f"read out value { value }")


register_service(SERVICE, get_secret_service)
