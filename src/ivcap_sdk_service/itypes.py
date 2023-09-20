#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
from enum import Enum
from typing import Dict, NamedTuple, Optional, Union
from numbers import Number

SCHEMA_KEY = "$schema"

# type
Url = str
MetaDict = Dict[str, Union[str, Number, bool]]
FilePath = str
ServiceArgs = NamedTuple


class SupportedMimeTypes(Enum):
    """
    An enumeration of supported MIME types for the IVCAP service SDK.

    Attributes:
        NETCDF (str): The MIME type for NetCDF files.
        PNG (str): The MIME type for PNG image files.
        JPEG (str): The MIME type for JPEG image files.
    """

    NETCDF = "application/netcdf"
    PNG = "image/png"
    JPEG = "image/jpeg"


class MissingParameterValue(Exception):
    """
    Exception raised when a required parameter is missing.

    Attributes:
        name (str): The name of the missing parameter.
        message (Optional[str]): An optional error message.
    """

    name: str
    message: Optional[str]

    def __init__(self, name: str, message: str = None):
        self.name = name
        self.message = message


class UnsupportedMimeType(Exception):
    """
    Exception raised when an unsupported MIME type is encountered.

    Attributes:
        mime_type (str): The unsupported MIME type.
    """

    mime_type: str

    def __init__(self, mime_type: str):
        self.mime_type = mime_type


class MissingSchemaDeclaration(Exception):
    """
    Exception raised when a schema declaration is missing.
    """

    pass
