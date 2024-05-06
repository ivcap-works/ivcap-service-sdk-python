#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
import json
from typing import Dict
from pydantic import RootModel, TypeAdapter
from pydantic.dataclasses import dataclass

from .itypes import URN

@dataclass
class Aspect():

    def to_dict(self) -> Dict[str, any]:
        if not hasattr(self, 'SCHEMA'):
            raise Exception("Missing 'SCHEMA' declaration")
        d = { '$schema':  self.SCHEMA }
        d.update(RootModel(self).model_dump(
            mode='json',
            by_alias=True,
            exclude_unset=True,
            exclude_none=True
        ))
        return d

    def dump_json(self, indent = 2, entity: URN = None) -> str:
        d = self.to_dict()
        if entity: d["$entity"] = entity
        return json.dumps(d, indent=indent)

    @classmethod
    def json_schema(cls, json_schema="https://json-schema.org/draft/2020-12/schema"):
        if not hasattr(cls, 'SCHEMA'):
            raise Exception("Missing 'SCHEMA' declaration")
        s = {
            "$schema": json_schema,
            "$id": cls.SCHEMA,
            "title": "" # filled in later
        }
        if hasattr(cls, 'DESCRIPTION'):
            s["description"] = cls.DESCRIPTION

        s.update(TypeAdapter(cls).json_schema())
        if hasattr(cls, 'TITLE'):
            s['title'] = cls.TITLE
        return s

class GenericAspect(Aspect):
    """Used for reading unknown aspects"""
    def __init__(self, schema: URN, **entries):
        entries.pop("$schema")
        self.__dict__.update(entries)
        self.SCHEMA = schema
        self.ENTITY = entries.get("$entity")

    def to_dict(self) -> Dict[str, any]:
        d = super().to_dict()
        d.update(self.__dict__)
        d.pop("SCHEMA")
        return d

    def __repr__(self):
        if self.ENTITY:
            return f"<GenericAspect schema={self.SCHEMA} entity={self.ENTITY}>"
        else:
            return f"<GenericAspect schema={self.SCHEMA}>"

    @classmethod
    def json_schema(cls, json_schema=None):
        raise Exception(f"json_schema: not a valid call for a '{cls}'")
