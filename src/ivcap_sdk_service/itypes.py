#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
from enum import Enum
from typing import Dict, NamedTuple, Optional, Union
from numbers import Number

SCHEMA_KEY = '$schema'
ENTITY_KEY = '$entity'

class SupportedMimeTypes(Enum):
    TEXT = 'text'
    CSV = 'text/csv'
    JSON = 'application/json'
    NETCDF = 'application/netcdf'
    PNG = 'image/png'
    JPEG = 'image/jpeg'
    PARQUET = "application/vnd.apache.parquet"

# type
URN = str
Url = str
AspectDict = Dict[str, Union[str, Number, bool]]
MetaDict = AspectDict
FilePath = str
ServiceArgs = NamedTuple

class MissingParameterValue(Exception):
    name: str
    message: Optional[str]

    def __init__(self, name: str, message:str = None):
        self.name = name
        self.message = message

class UnsupportedMimeType(Exception):
    mime_type: str

    def __init__(self, mime_type: str):
        self.mime_type = mime_type

class MissingSchemaDeclaration(Exception):
    pass

class MissingFile(Exception):
    fname: str

    def __init__(self, fname: str):
        self.fname = fname
