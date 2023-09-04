#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
from __future__ import annotations
from argparse import Action, ArgumentTypeError
import yaml
import validators

from .ivcap import get_config
from .config import Resource, INSIDE_CONTAINER

# TODO: Add verifying code
def verify_artifact(urn):
    if is_valid_resource_urn(urn, Resource.ARTIFACT):
        return urn

    # if INSIDE_CONTAINER:
    #     if not validators.url(urn):
    #         raise ArgumentTypeError(f"Illegal artifact reference '{urn}' - expected url")
    #     return urn
    # else:
    
    if validators.url(urn):
        return urn
    # could be local file 
    if not get_config().IO_ADAPTER.artifact_readable(urn):
        raise ArgumentTypeError(f"Cannot find local file '{urn}' - {get_config().IO_ADAPTER}")
    return urn

class ArtifactAction(Action):
    def __call__(self, _1, namespace, value, _2=None):
        try:
            v = get_config().IO_ADAPTER.read_artifact(value)
            setattr(namespace, self.dest, v)
        except Exception as err:
            raise ArgumentTypeError(err)

def verify_collection(urn: str):
    if is_valid_resource_urn(urn, Resource.COLLECTION):
        return urn
    if is_valid_resource_urn(urn, Resource.ARTIFACT):
        # treating a artifact as a collection of ONE
        return urn


    if INSIDE_CONTAINER:
        # inside a container we get collections served from a queue
        if urn.startswith(get_config().QUEUE_PREFIX):
            return urn
        
        raise ArgumentTypeError(f"Illegal collection reference '{urn}' - expected url")
    else:
        # throws an exception if we can't create a collection object
        get_config().IO_ADAPTER.get_collection(urn)
        return urn 

class CollectionAction(Action):
    def __call__(self, _1, namespace, value, _2=None):
        try:
            v = get_config().IO_ADAPTER.get_collection(value)
            setattr(namespace, self.dest, v)
        except Exception as err:
            raise ArgumentTypeError(err)
        
def is_valid_resource_urn(urn: str, resource: Resource) -> bool:
    prefix = f"{get_config().SCHEMA_PREFIX}{resource.value}:"
    return urn.startswith(prefix)
