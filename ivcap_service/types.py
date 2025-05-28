#
# Copyright (c) 2025 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
import io
from typing import Any, Optional, Union
from dataclasses import dataclass
from pydantic import ConfigDict, Field, BaseModel

from .events import EventReporter

class ExecutionContext:
    pass

class JobContext(BaseModel):
    job_id: Optional[str]
    report: EventReporter
    job_authorization: Optional[str]

    model_config = ConfigDict(arbitrary_types_allowed=True)

@dataclass
class BinaryResult():
    """If the result of the tool is a non json serialisable object, return an
    instance of this class indicating the content-type and the actual
    result either as a byte array or a file handle to a binary content (`open(..., "rb")`)"""
    content_type: str = Field(description="Content type of result serialised")
    content: Union[bytes, str, io.BufferedReader] = Field(description="Content to send, either as byte array or file handle")

@dataclass
class IvcapResult(BinaryResult):
    isError: bool = False
    raw: Any = None

class ExecutionError(BaseModel):
    """
    Pydantic model for execution errors.
    """
    jschema: str = Field("urn:ivcap:schema.ai-tool.error.1", alias="$schema")
    error: str = Field(description="Error message")
    type: str = Field(description="Error type")
    traceback: Optional[str] = Field(None, description="traceback")
