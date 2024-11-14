#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
from enum import Enum
from typing import Any
import yaml
import json
import requests
import time
import os

from .logger import sys_logger as logger
from .aspect import Aspect
from .itypes import URN

try:
    from yaml import CSafeLoader as SafeLoader, CDumper as Dumper
except ImportError:
    from yaml import SafeLoader, Dumper

class Context(Enum):
    ARGO = "argo"
    LAMBDA = "lambda"
    SERVER = "server"

def get_context() -> Context:
    from .ivcap import get_config

    if os.getenv('ARGO_NODE_ID', None):
        return Context.ARGO
    if get_config().SERVICE_URL:
        return Context.SERVER
    return Context.LAMBDA

def use_data_proxy() -> bool:
    if os.getenv('http_proxy', None):
        return True
    if os.getenv('https_proxy', None):
        return True
    return False



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

def json_dump(obj: Any, fileName: str = None, entity: URN = None, failQuietly=True) -> str:
    try:
        if isinstance(obj, Aspect):
            js = obj.dump_json(indent=2, entity=entity)
        else:
            d = obj if isinstance(obj, dict) else obj.__dict__
            if not d.get("$schema"):
                logger.warning("metadata has no '$schema' declaration - {d}")
            if entity: d["$entity"] = entity
            js = json.dumps(obj, indent=2, cls=_CustomEncoder)
        if fileName:
            with open(fileName, "w") as fp:
                fp.write(js)
        return js
    except BaseException as err:
        logger.warning(f"json_dump: serialising '{obj}' failed with '{err}'")
        if failQuietly:
            return "{}"
        else:
            raise err

def get_banner(service: "BaseService"):
    from .__init__ import __version__


    sdk_v = os.getenv('IVCAP_SDK_VERSION', __version__)
    svc_v = os.getenv('IVCAP_SERVICE_VERSION', '?')
    svc_c = os.getenv('IVCAP_SERVICE_COMMIT', '?')
    svc_d = os.getenv('IVCAP_SERVICE_BUILD', '?')

    return f"IVCAP Service '{service.name}' {svc_v}/{svc_c} (sdk {sdk_v}) built on {svc_d}."

def print_banner(service: "BaseService"):
    logger.info(get_banner(service))

def wait_for_data_proxy():
    from .ivcap import get_config

    if not use_data_proxy():
        return

    url = f"{get_config().STORAGE_URL}/readyz"
    retries = int(os.getenv('IVCAP_DATA_PROXY_RETRIES', 5))
    delay = int(os.getenv('IVCAP_DATA_PROXY_DELAY', 3))

    for _ in range(retries):
        logger.info(f"Checking for data-proxy at '{url}'.")
        try:
            requests.head(url)
            return
        except Exception:
            logger.info(f"Data-proxy doesn't seem to be ready yet, will wait {delay}sec and try again.")
            time.sleep(delay)
    raise Exception(f"Can't contact data-proxy after {retries} retries on '{url}'")
