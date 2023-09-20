#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
from typing import Any
import json
import yaml

from .logger import sys_logger as logger

try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader


# Remove date parsing of yaml as datetime not serializable
# https://stackoverflow.com/questions/34667108/ignore-dates-and-times-while-parsing-yaml
class NoDatesSafeLoader(SafeLoader):
    """
    A YAML loader that safely loads basic Python objects but ignores datetime strings.

    This class is used to load YAML data that may contain datetime strings, but
    we want to treat them as plain strings instead of dates. This is because we
    later serialize the data as JSON, which doesn't support advanced types like
    dates, and this can cause compatibility issues down the line.

    To use this loader, simply pass it to the `yaml.load()` function, like this:

        data = yaml.load(yaml_string, Loader=NoDatesSafeLoader)

    """

    @classmethod
    def remove_implicit_resolver(cls, tag_to_remove):
        """
        Remove implicit resolvers for a particular tag.

        Takes care not to modify resolvers in super classes.

        We want to load datetimes as strings, not dates, because we
        go on to serialise as json which doesn't have the advanced types
        of yaml, and leads to incompatibilities down the track.
        """
        if "yaml_implicit_resolvers" not in cls.__dict__:
            cls.yaml_implicit_resolvers = cls.yaml_implicit_resolvers.copy()

        for first_letter, mappings in cls.yaml_implicit_resolvers.items():
            cls.yaml_implicit_resolvers[first_letter] = [
                (tag, regexp) for tag, regexp in mappings if tag != tag_to_remove
            ]


def read_json(file_name):
    """
    Reads a JSON file and returns its contents as a dictionary.

    Args:
        file_name (str): The name of the JSON file to read.

    Returns:
        dict: The contents of the JSON file as a dictionary.
    """
    with open(file_name, "r") as f:
        data = f.read()
        params = json.loads(data)
        return params


def read_yaml(file_name):
    """
    Reads a YAML file and returns its contents as a dictionary.

    Args:
        file_name (str): The name of the YAML file to read.

    Returns:
        dict: The contents of the YAML file as a dictionary.
    """
    with open(file_name, "r") as f:
        params = yaml.safe_load(f)
        return params


def read_yaml_no_dates(file_name):
    """
    Reads a YAML file and returns its contents as a dictionary, without parsing any dates.

    Args:
        file_name (str): The path to the YAML file to read.

    Returns:
        dict: The contents of the YAML file, as a dictionary.
    """
    NoDatesSafeLoader.remove_implicit_resolver("tag:yaml.org,2002:timestamp")
    with open(file_name, "r") as f:
        params = yaml.load(f, Loader=NoDatesSafeLoader)
        return params


class _CustomEncoder(json.JSONEncoder):
    def default(self, o):
        if "tojson" in dir(o):
            return o.tojson()
        if "to_json" in dir(o):
            return o.to_json()
        return json.JSONEncoder.default(self, o)


def json_dump(obj: Any, file_name: str = None, fail_quietly=True) -> str:
    """
    Serializes the given object to a JSON string and optionally writes it to a file.

    Args:
        obj (Any): The object to serialize.
        fileName (str, optional): The name of the file to write the JSON string to. Defaults to None.
        failQuietly (bool, optional): Whether to return an empty JSON object if serialization fails. Defaults to True.

    Returns:
        str: The JSON string representation of the object.
    """
    try:
        js = json.dumps(obj, indent=2, cls=_CustomEncoder)
        if file_name:
            with open(file_name, "w") as fp:
                fp.write(js)
        return js
    except BaseException as err:
        logger.warning(f"json_dump: serialising '{obj}' failed with '{err}'")
        if fail_quietly:
            return "{}"
        else:
            raise err
