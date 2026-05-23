#
# Copyright (c) 2025 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
from dataclasses import dataclass
from typing import Any, BinaryIO

from ivcap_client.ivcap import IVCAP
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from .events import EventReporter


class ExecutionContext:
    pass


class JobContext(BaseModel):
    job_id: str | None = None
    report: EventReporter | None = None
    job_authorization: str | None = None

    _ivcap: IVCAP | None = PrivateAttr(None)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def ivcap(self) -> IVCAP | None:
        if self._ivcap is None:
            self._ivcap = IVCAP()
        return self._ivcap


@dataclass
class BinaryResult:
    """If the result of the tool is a non json serialisable object, return an
    instance of this class indicating the content-type and the actual
    result either as a byte array or a file handle to a binary content (`open(..., "rb")`)"""

    content_type: str = Field(description="Content type of result serialised")
    content: bytes | str | BinaryIO = Field(
        description="Content to send, either as byte array or file handle"
    )


@dataclass
class IvcapResult(BinaryResult):
    isError: bool = False
    raw: Any = None


class ExecutionError(BaseModel):
    """
    Pydantic model for execution errors.
    """

    jschema: str = Field(
        default="urn:ivcap:schema.service.error.1",
        validation_alias="$schema",
        serialization_alias="$schema",
    )
    error: str = Field(description="Error message")
    type: str = Field(description="Error type")
    traceback: str | None = Field(default=None, description="traceback")

    model_config = {
        "populate_by_name": True,
    }
