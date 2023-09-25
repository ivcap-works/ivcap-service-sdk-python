#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#

from __future__ import annotations
from dataclasses import dataclass, field
from dataclass_wizard import JSONWizard, json_field
from argparse import ArgumentParser
from typing import List, Any
import yaml
from enum import Enum
import os

from typing import Dict

from .verifiers import verify_artifact, verify_collection, ArtifactAction, CollectionAction
from .utils import read_yaml_no_dates

@dataclass
class Option:
    """Defines one option of a `Parameter` of type `OPTION`
    """
    value: str
    name: str = None
    description: str = None

class Type(Enum):
    """Enumerates the different types of service `Parameters`
    """
    STRING = 'string'
    INT = 'int'
    FLOAT = 'float'
    BOOL = 'bool'
    OPTION = 'option'
    ARTIFACT = 'artifact'
    COLLECTION = 'collection'

@dataclass()
class Parameter(JSONWizard):
    """Defines a `Service` parameter
    """
    class _(JSONWizard.Meta):
        skip_defaults = True

    name: str
    type: Type
    options: List[Option] = None
    description: str = None
    default: Any = None
    unit: str = None
    help: str = None
    optional: bool = False
    constant: bool = False

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

@dataclass
class Workflow(JSONWizard):
    """Defines the workflow associated with a `Service`"""
    class _(JSONWizard.Meta):
        skip_defaults = False

    type: str

@dataclass
class BasicWorkflow(Workflow):
    """Defines an IVCAP 'Service' workflow consisting of a single container

    Args:
        image (str): Name of docker image ['IVCAP_CONTAINER', '@CONTAINER@']
        command (str): Path to init executable/script
        min_memory (int): Min memory requirement in ???
    """
    type: str = "basic"
    image: str = os.getenv('IVCAP_CONTAINER', '@CONTAINER@')
    command: List[str] = field(default_factory=list)
    min_memory: str = None

    def to_dict(self):
        basic = {
            'command': self.command,
            'image': self.image
        }
        if self.min_memory:
            basic['memory'] = { 'request': self.min_memory}
        return {
            'type': 'basic',
            'basic': basic
        }

@dataclass
class PythonWorkflow(BasicWorkflow):
    """Defines an IVCAP 'Service' workflow consisting of a single python script

    Args:
        image (str): Name of docker image ['IVCAP_CONTAINER', '@CONTAINER@']
        script (str): Path to main python script ['/app/service.py']
        min_memory (int): Min memory requirement in ???
    """
   
    script: str = '/app/service.py'

    @classmethod
    def def_workflow(cls): 
        return cls()

    def to_dict(self):
        d = super().to_dict()
        d['basic']['command'] = ['python', self.script]
        return d

@dataclass
class Service(JSONWizard):
    """Defines an IVCAP service with all it's necessary components

    Args:
        id(URN): Service URN ['IVCAP_SERVICE_ID', '@SERVICE_ID@']
        name(str): Human friendly service name
        description(str): Detailed description of this service
        providerID(URN): Provider URN ['IVCAP_PROVIDER_ID', '@PROVIDER_ID@']
        accountID(URN): Account URN ['IVCAP_ACCOUNT_ID', '@ACCOUNT_ID@']
        parameters(List[Parameter]): List of parameters for this service
        workflow(Workflow): Workflow to use when executing the service [PythonWorkflow]

    """
    # class _(JSONWizard.Meta):
    #     skip_defaults = True

    name: str
    id: str = os.getenv('IVCAP_SERVICE_ID', '@SERVICE_ID@')
    providerID: str = json_field('provider-id', all=True, default=os.getenv('IVCAP_PROVIDER_ID', '@PROVIDER_ID@'))
    accountID: str = json_field('account-id', all=True, default=os.getenv('IVCAP_ACCOUNT_ID', '@ACCOUNT_ID@'))
    parameters: List[Parameter] = field(default_factory=list)
    description: str = None
    workflow: Workflow = field(default_factory=PythonWorkflow.def_workflow)

    @classmethod
    def from_file(cls, serviceFile: str) -> None:
        pd = read_yaml_no_dates(serviceFile)
        return cls.from_dict(pd)

    # this function is NOT calling the 'to_dict' of referenced JSONWizard classes
    def to_dict(self):
        d = super().to_dict()
        d['parameters'] = list(map(lambda p: p.to_dict(), self.parameters))
        d['workflow'] = self.workflow.to_dict()
        return d

    def to_yaml(self) -> str:
        as_dict = self.to_dict()
        as_yaml = yaml.dump(as_dict, default_flow_style=False, default_style='"')
        return as_yaml

    def append_arguments(self, ap: ArgumentParser) -> ArgumentParser:
        type2type = {
            Type.STRING: str,
            Type.INT: int,
            Type.FLOAT: float,
            Type.BOOL: bool,
        }
        # optionals = []
        for p in self.parameters:
            if not (p.name and p.type):
                raise Exception(f"A service parameter needs at least a name and a type - {p}")
            name = p.name
            if name.startswith('cre:') or name.startswith('ivcap:'):
                continue
            args:Dict[str, Any] = dict(required = True)
            if p.type == Type.OPTION:
                ca = list(map(lambda o: o.value, p.options))
                args['choices'] = ca      
            elif p.type == Type.ARTIFACT:
                args['type'] = verify_artifact
                args['metavar'] = "URN"
                args['action'] = ArtifactAction
                pass
            elif p.type == Type.COLLECTION:
                args['type'] = verify_collection
                args['metavar'] = "URN"
                args['action'] = CollectionAction
                pass
            elif p.type == Type.BOOL:
                args['action'] ='store_true'
                args['required'] = False
            else:
                if not type(p.type) == Type:
                    raise Exception(f"Wrong type declaration for '{name}' - use enum 'Type'")
                   
                t = type2type.get(p.type)
                if not t:
                    raise Exception(f"Unsupported type '{p.type}' for '{name}'")
                args['type'] = t
                args['metavar'] = p.type.name.upper()
            if p.default:
                args['default'] = p.default
            if p.description:
                if p.default:
                    args['help'] = f"{p.description} [{p.default}]"
                else:
                    args['help'] = f"{p.description}"
            if p.optional:
                args['required'] = not p.optional
                # optionals.append(name)
            if p.constant or p.default:
                args['required'] = False
            ap.add_argument(f"--{name}", **args)
        return ap


