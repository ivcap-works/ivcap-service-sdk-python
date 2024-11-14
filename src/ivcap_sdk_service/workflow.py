from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Callable, List, Sequence
import yaml
import os
from argparse import ArgumentParser
from collections import namedtuple

from typing import Dict

from .utils import read_yaml_no_dates
from .logger import logger, sys_logger
from .service import BaseService

class Workflow(BaseModel):
    """Defines the workflow associated with a `Service`"""
    # class _(JSONWizard.Meta):
    #     skip_defaults = False

    type: str

class BasicWorkflow(Workflow):
    """Defines an IVCAP 'Service' workflow consisting of a single container

    Args:
        image (str): Name of docker image ['IVCAP_CONTAINER', '@CONTAINER@']
        command (str): Path to init executable/script
        min_memory (int): Min memory requirement in ???
        min_cpu (int): Min cpu requirement in ???
        min_ephemeral_storage (int): Min ephemeral storage requirement in ???
        gpu_type: only nvidia-tesla-t4 allowed for now, check the avalibility at https://cloud.google.com/compute/docs/gpus/gpu-regions-zones and
                  https://cloud.google.com/kubernetes-engine/docs/how-to/autopilot-gpus#use-cases
        gpu_number: specify the number of gpu cards, 1,2 or 4 allowed for now.
    """
    type: str = "basic"
    image: str = os.getenv('IVCAP_CONTAINER', '@CONTAINER@')
    command: List[str] = Field(default_factory=list)
    min_memory: str = None
    min_cpu:    str = None
    min_ephemeral_storage: str = None
    gpu_type:   str = None
    gpu_number: int = 0

    def to_dict(self):
        basic = {
            'command': self.command,
            'image': self.image
        }
        if self.gpu_type:
            basic['gpu-type'] = self.gpu_type
        if self.gpu_number:
            basic['gpu-number'] = self.gpu_number
        if self.min_memory:
            basic['memory'] = {'request': self.min_memory}
        if self.min_cpu:
            basic['cpu'] = {'request': self.min_cpu}
        if self.min_ephemeral_storage:
            basic['ephemeral-storage'] = {'request': self.min_ephemeral_storage}
        return {
            'type': 'basic',
            'basic': basic
        }

class PythonWorkflow(BasicWorkflow):
    """Defines an IVCAP 'Service' workflow consisting of a single python script

    Args:
        image (str): Name of docker image ['IVCAP_CONTAINER', '@CONTAINER@']
        script (str): Path to main python script ['/app/service.py']
        min_memory (int): Min memory requirement in ???
        min_cpu (int): Min cpu requirement in ???
        min_ephemeral_storage (int): Min ephemeral storage requirement in ???
    """

    script: str = '/app/service.py'

    @classmethod
    def def_workflow(cls):
        return cls()

    def to_dict(self):
        d = super().to_dict()
        d['basic']['command'] = ['python', self.script]
        return d

class Service(BaseService):
    """Defines an IVCAP service with all it's necessary components

    Args:
        id(URN): Service URN ['IVCAP_SERVICE_ID', '@SERVICE_ID@']
        name(str): Human friendly service name
        description(str): Detailed description of this service
        accountID(URN): Account URN ['IVCAP_ACCOUNT_ID', '@ACCOUNT_ID@']
        parameters(List[Parameter]): List of parameters for this service
        workflow(Workflow): Workflow to use when executing the service [PythonWorkflow]

    """
    # class _(JSONWizard.Meta):
    #     skip_defaults = True

    workflow: Workflow = Field(default_factory=PythonWorkflow.def_workflow)


    @classmethod
    def from_file(cls, serviceFile: str) -> 'Service':
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

    def run(args: Dict, handler: Callable[[Dict], int]) -> int:
        sys_logger.info(f"Starting service with '{args}'")
        code = handler(args, logger)


    def run_service(service: Service, args: Sequence[str], handler: Callable[[Dict], int]) -> int:
        ap = ArgumentParser(description=service.description)
        # Need to wait for 3.10
        # ap = ArgumentParser(description=service.description, exit_on_error=False)
        service.append_arguments(ap)
        pargs = ap.parse_args(args)
        args = vars(pargs)
        ST = namedtuple('ServiceArgs', args.keys())
        at = ST(**args)
        return run(at, handler)
