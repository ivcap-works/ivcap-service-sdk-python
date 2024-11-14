#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
import json
from typing import Dict
from pydantic import RootModel, TypeAdapter, BaseModel, Field
from pydantic.dataclasses import dataclass

from .itypes import URN

class BaseAspect:

    def to_dict(self, entity: URN = None) -> Dict[str, any]:
        if not hasattr(self, 'SCHEMA'):
            raise Exception("Missing 'SCHEMA' declaration")
        d = { '$schema':  self.SCHEMA }
        if entity: d["$entity"] = entity
        d.update(RootModel(self).model_dump(
            mode='json',
            by_alias=True,
            exclude_unset=True,
            exclude_none=True
        ))
        return d

    def model_dump(self, **args):
        opts = {
            "mode": 'json',
            "by_alias": True,
            "exclude_unset": True,
            "exclude_none": True,
        }
        opts.update(**args)
        return RootModel(self).model_dump(**opts)

    def dump_json(self, indent = 2, entity: URN = None) -> str:
        d = self.to_dict(entity)
        return json.dumps(d, indent=indent)

    @classmethod
    def schema(cls):
        if not hasattr(cls, 'SCHEMA'):
            raise Exception("Missing 'SCHEMA' declaration")
        return cls.SCHEMA


    @classmethod
    def json_schema(cls, *, exclude_entity=False, json_schema="https://json-schema.org/draft/2020-12/schema"):
        if not hasattr(cls, 'SCHEMA'):
            raise Exception("Missing 'SCHEMA' declaration")
        s = {
            "$schema": json_schema,
            "$id": cls.SCHEMA,
            "title": "" # filled in later
        }
        if hasattr(cls, 'DESCRIPTION'):
            s["description"] = cls.DESCRIPTION

        t = TypeAdapter(cls)
        s.update(t.json_schema())
        if exclude_entity:
            p = s["properties"]
            del p['$entity']
        if hasattr(cls, 'TITLE'):
            s['title'] = cls.TITLE
        return s

class Aspect(BaseAspect, BaseModel):
    entity: URN = Field(None, description="URN of entity this aspect is for", alias='$entity')


class GenericAspect(BaseAspect):
    """Used for reading unknown aspects"""
    def __init__(self, schema: URN, **entries):
        entries.pop("$schema", None)
        self.__dict__.update(entries)
        self.SCHEMA = schema
        self.ENTITY = entries.get("$entity")

    def to_dict(self, entity: URN = None) -> Dict[str, any]:
        d = {
            "$schema": self.SCHEMA
        }
        if self.ENTITY or entity:
            d["$entity"] = self.ENTITY if self.ENTITY else entity
        v = vars(self)
        v.pop("SCHEMA")
        v.pop("ENTITY")
        d.update(v)
        return d

    def __repr__(self):
        if self.ENTITY:
            return f"<GenericAspect schema={self.SCHEMA} entity={self.ENTITY}>"
        else:
            return f"<GenericAspect schema={self.SCHEMA}>"

    @classmethod
    def json_schema(cls, json_schema=None):
        raise Exception(f"json_schema: not a valid call for a '{cls}'")
