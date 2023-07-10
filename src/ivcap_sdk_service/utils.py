#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
from typing import Any
import yaml
import json
from typing import Any
import yaml

from .logger import sys_logger as logger

try:
    from yaml import CSafeLoader as SafeLoader, CDumper as Dumper
except ImportError:
    from yaml import SafeLoader, Dumper

# Remove date parsing of yaml as datetime not serializable
# https://stackoverflow.com/questions/34667108/ignore-dates-and-times-while-parsing-yaml
class NoDatesSafeLoader(SafeLoader):
    """Used to safely load basic python objects but ignore datetime strings."""

    @classmethod
    def remove_implicit_resolver(cls, tag_to_remove):
        """
        Remove implicit resolvers for a particular tag.

        Takes care not to modify resolvers in super classes.

        We want to load datetimes as strings, not dates, because we
        go on to serialise as json which doesn't have the advanced types
        of yaml, and leads to incompatibilities down the track.
        """
        if 'yaml_implicit_resolvers' not in cls.__dict__:
            cls.yaml_implicit_resolvers = cls.yaml_implicit_resolvers.copy()

        for first_letter, mappings in cls.yaml_implicit_resolvers.items():
            cls.yaml_implicit_resolvers[first_letter] = [
                (tag, regexp)
                for tag, regexp in mappings if tag != tag_to_remove
            ]

def read_json(file_name):
    with open(file_name, 'r') as f:
        data = f.read()
        params = json.loads(data)
        return params

def read_yaml(file_name):
    with open(file_name, 'r') as f:
        params = yaml.safe_load(f)
        return params

def read_yaml_no_dates(file_name):
    NoDatesSafeLoader.remove_implicit_resolver('tag:yaml.org,2002:timestamp')
    with open(file_name, 'r') as f:
        params = yaml.load(f,Loader=NoDatesSafeLoader)
        return params

class _CustomEncoder(json.JSONEncoder):
    def default(self, o):
        if "tojson" in dir(o):
            return o.tojson()
        if "to_json" in dir(o):
            return o.to_json()
        return json.JSONEncoder.default(self, o)

def json_dump(obj: Any, fileName: str = None, failQuietly=True) -> str:
    try:
        js = json.dumps(obj, indent=2, cls=_CustomEncoder)
        if fileName:
            with open(fileName, "w") as fp:
                fp.write(js)
        return js
    except BaseException as err:
        logger.warn(f"json_dump: serialising '{obj}' failed with '{err}'")
        if failQuietly:
            return "{}"
        else:
            raise err
