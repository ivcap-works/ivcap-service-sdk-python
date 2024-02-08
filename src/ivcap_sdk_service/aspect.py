import json
from typing import Dict
from pydantic import RootModel, TypeAdapter
from pydantic.dataclasses import dataclass

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

    def dump_json(self, indent = 2) -> str:
        d = self.to_dict()
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