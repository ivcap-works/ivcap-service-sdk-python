#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#

from __future__ import annotations
from pydantic import BaseModel, field_serializer, Field, field_validator
from typing import Callable, List, Any, Optional, Sequence, Union, Type as TypeT
import yaml
import sys
from enum import Enum
import os
from argparse import ArgumentParser, ArgumentError
from collections import namedtuple

from typing import Dict

from ivcap_sdk_service.itypes import URN

from .verifiers import QueueAction, verify_artifact, verify_collection, ArtifactAction
from .verifiers import verify_aspect, AspectAction, CollectionAction, verify_queue
from .utils import read_yaml_no_dates, print_banner, wait_for_data_proxy
from .ivcap import init, get_config
from .logger import logger, sys_logger
from .config import Command, Config
from .utils import get_context, Context, use_data_proxy
from .aspect import Aspect


class Option(BaseModel):
    """Defines one option of a `Parameter` of type `OPTION`
    """
    value: str
    name: str = None
    description: str = None

class Type(Enum):
    """Enumerates the different types of service `Parameters`
    """
    STRING = 'string'
    URN = 'urn'
    INT = 'int'
    FLOAT = 'float'
    BOOL = 'bool'
    OPTION = 'option'
    ARTIFACT = 'artifact'
    ASPECT = 'aspect'
    COLLECTION = 'collection'
    QUEUE = 'queue'

class BaseParameter(BaseModel):
    name: str
    type: Type
    description: str = None
    help: str = None
    optional: bool = False
    constant: bool = False
    default: Any = None
    options: List[Option] = None
    unit: str = None
    unary: bool = False

    def __post_init__(self):
        # 'default' is supposed to be a string
        self.default = self._to_str(self.default)

    def to_dict(self):
        d = super().to_dict()
        if self.type == Type.BOOL and not self.default:
            d['optional'] = True
        return d

    def _to_str(self, v):
        if v != None and type(v) != str:
            return str(v)
        else:
            return v

    def append_arguments(self, ap: ArgumentParser) -> None:
        type2type = {
            Type.STRING: str,
            Type.URN: URN,
            Type.INT: int,
            Type.FLOAT: float,
            Type.BOOL: bool,
        }
        if not (self.name and self.type):
            raise Exception(f"A service parameter needs at least a name and a type - {p}")
        name = self.name
        if name.startswith('cre:') or name.startswith('ivcap:'):
            return
        args:Dict[str, Any] = dict(required = True)
        if self.type == Type.OPTION:
            ca = list(map(lambda o: o.value, self.options))
            args['choices'] = ca
        elif self.type == Type.ARTIFACT:
            args['type'] = verify_artifact
            args['metavar'] = "URN"
            args['action'] = ArtifactAction
            pass
        elif self.type == Type.ASPECT:
            args['type'] = verify_aspect
            args['metavar'] = "URN"
            args['action'] = AspectAction
            pass
        elif self.type == Type.COLLECTION:
            args['type'] = verify_collection
            args['metavar'] = "URN"
            args['action'] = CollectionAction
            pass
        elif self.type == Type.QUEUE:
            args['type'] = verify_queue
            args['metavar'] = "URN"
            args['action'] = QueueAction
        elif self.type == Type.BOOL:
            args['action'] ='store_true'
            args['required'] = False
        else:
            if not type(self.type) == Type:
                raise Exception(f"Wrong type declaration for '{name}' - use enum 'Type'")

            t = type2type.get(self.type)
            if not t:
                raise Exception(f"Unsupported type '{self.type}' for '{name}'")
            args['type'] = t
            args['metavar'] = self.type.name.upper()
        if self.default:
            args['default'] = self.default
        if self.description:
            if self.default:
                args['help'] = f"{self.description} [{self.default}]"
            else:
                args['help'] = f"{self.description}"
        if self.optional:
            args['required'] = not self.optional
            # optionals.append(name)
        if self.constant or self.default:
            args['required'] = False
        ap.add_argument(f"--{name}", **args)


class Parameter(BaseParameter):
    """Defines a `Service` parameter
    """
    # class _(JSONWizard.Meta):
    #     skip_defaults = True


class Contact(BaseModel):
    name: str
    email: str

class LicenseInfo(BaseModel):
    url: str
    name: str = None

class BaseService(BaseModel):
    """Defines an IVCAP service with all it's necessary components

    Args:
        id(URN): Service URN ['IVCAP_SERVICE_ID', '@SERVICE_ID@']
        name(str): Human friendly service name
        description(str): Detailed description of this service
        accountID(URN): Account URN ['IVCAP_ACCOUNT_ID', '@ACCOUNT_ID@']
        parameters(List[Parameter]): List of parameters for this service

    """
    # class _(JSONWizard.Meta):
    #     skip_defaults = True

    name: str
    id: str = os.getenv('IVCAP_SERVICE_ID', '@SERVICE_ID@')
    title: str = None
    description: str = None
    contact: Contact = None
    license_info: LicenseInfo = None
    accountID: str = Field(os.getenv('IVCAP_ACCOUNT_ID', '@ACCOUNT_ID@'), alias='account-id')
    parameters: List[BaseParameter] = Field(description="list of paramters accepted by this service")

    @field_serializer("parameters")
    @staticmethod
    def serialize_parameters(parameters: List[BaseParameter]) -> dict:
        d = list(map(lambda p: p.model_dump(exclude_unset=True), parameters))
        return d


    def _run(self, handler: Callable[[Dict], int]):
        if use_data_proxy():
            # print banner immediately when inside the cluster
            print_banner(self)

        init(None, self._append_sys_arguments)
        cmd = self._get_command(get_config())
        if not cmd:
            return # sub class took care of it

        if cmd == Command.SERVICE_RUN:
            if not use_data_proxy():
                print_banner(self)
            wait_for_data_proxy()
            cfg = get_config()
            sys_logger.info(f"Starting job for service '{self.name}' on node '{cfg.NODE_ID}' ({cfg.ORDER_ID})")
            try:
                ap = ArgumentParser(description=self.description)
                # Need to wait for 3.10
                # ap = ArgumentParser(description=service.description, exit_on_error=False)
                self._append_run_arguments(ap)
                pargs = ap.parse_args(cfg.SERVICE_ARGS)
                args = vars(pargs)
                ST = namedtuple('ServiceArgs', args.keys())
                at = ST(**args)
                code = handler(at)
                sys.exit(code)
            except ArgumentError as perr:
                sys_logger.fatal(f"arg error '{perr}'")
            except Exception as err:
                sys_logger.exception(err)
                sys.exit(-1)
        elif cmd == Command.SERVICE_FILE:
            print(self.to_yaml())
        elif cmd == Command.SERVICE_HELP:
            ap = ArgumentParser(description=self.description, add_help=False)
            self.append_arguments(ap)
            ap.print_help()
        else:
            sys_logger.error(f"Unexpected command '{cmd}'")

    def _get_command(self, cfg: Config) -> Optional[Command]:
        """Return the command to execute or None if it has been taken care of
        """
        return cfg.SERVICE_COMMAND

    def _append_sys_arguments(self, ap: ArgumentParser) -> ArgumentParser:
        return ap

    def _append_run_arguments(self, ap: ArgumentParser) -> ArgumentParser:
        for p in self.parameters:
            p.append_arguments(ap)
        return ap
