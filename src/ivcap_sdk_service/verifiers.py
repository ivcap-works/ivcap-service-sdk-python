#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
from __future__ import annotations
from argparse import Action, ArgumentTypeError
import validators

from .ivcap import get_config
from .config import Resource, INSIDE_CONTAINER


# TODO: Add verifying code
def verify_artifact(urn):
    """
    Verifies that the given URN is a valid artifact reference.

    Args:
        urn (str): The URN to verify.

    Returns:
        str: The verified URN.

    Raises:
        ArgumentTypeError: If the URN is not a valid artifact reference.
    """
    if is_valid_resource_urn(urn, Resource.ARTIFACT):
        return urn

    if validators.url(urn):
        return urn

    # could be local file
    if not get_config().IO_ADAPTER.artifact_readable(urn):
        raise ArgumentTypeError(
            f"Cannot find local file '{urn}' - {get_config().IO_ADAPTER}"
        )
    return urn


class ArtifactAction(Action):
    """
    A custom argparse action that reads an artifact from the given value and sets it as an attribute on the namespace.

    Args:
        _1: Unused.
        namespace: The namespace to set the attribute on.
        value: The value to read the artifact from.
        _2: Unused.

    Raises:
        ArgumentTypeError: If there was an error reading the artifact.
    """

    def __call__(self, _1, namespace, value, _2=None):
        try:
            artifact_content = get_config().IO_ADAPTER.read_artifact(value)
            setattr(namespace, self.dest, artifact_content)
        except Exception as err:
            raise ArgumentTypeError(err)


def verify_collection(urn: str):
    """
    Verifies that the given URN is a valid collection reference.

    Args:
        urn (str): The URN to verify.

    Returns:
        str: The verified URN.

    Raises:
        ArgumentTypeError: If the URN is not a valid collection reference.
    """
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
    """
    An argparse action that retrieves a collection from the IO adapter and sets it as an attribute on the namespace.

    Args:
        _1: Unused.
        namespace: The namespace to set the attribute on.
        value: The name of the collection to retrieve.
        _2: Unused.
    """

    def __call__(self, _1, namespace, value, _2=None):
        try:
            collection = get_config().IO_ADAPTER.get_collection(value)
            setattr(namespace, self.dest, collection)
        except Exception as err:
            raise ArgumentTypeError(err)


def is_valid_resource_urn(urn: str, resource: Resource) -> bool:
    """
    Check if the given URN is valid for the specified resource.

    Args:
        urn (str): The URN to check.
        resource (Resource): The resource to check the URN against.

    Returns:
        bool: True if the URN is valid for the specified resource, False otherwise.
    """
    prefix = f"{get_config().SCHEMA_PREFIX}{resource.value}:"
    return urn.startswith(prefix)
