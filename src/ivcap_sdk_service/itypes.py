#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
from enum import Enum
from typing import Dict, NamedTuple, Optional, Union
from numbers import Number

SCHEMA_KEY = '$schema'

class SupportedMimeTypes(Enum):
    NETCDF = 'application/netcdf'
    PNG = 'image/png'
    JPEG = 'image/jpeg'

# type
Url = str
MetaDict = Dict[str, Union[str, Number, bool]]
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
