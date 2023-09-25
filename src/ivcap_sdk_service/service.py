#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
from __future__ import annotations

from argparse import ArgumentParser
from typing import Dict, List, Any
from enum import Enum
import os

from dataclasses import dataclass, field
from dataclass_wizard import JSONWizard, json_field
import yaml

from .verifiers import (
    verify_artifact,
    verify_collection,
    ArtifactAction,
    CollectionAction,
)
from .utils import read_yaml_no_dates


@dataclass
class Option:
    """
    Defines one option of a `Parameter` of type `OPTION`.

    Attributes:
        value (str): The value of the option.
        name (str, optional): The name of the option. Defaults to None.
        description (str, optional): A description of the option. Defaults to None.
    """

    value: str
    name: str = None
    description: str = None


class Type(Enum):
    """Enumerates the different types of service `Parameters`

    Attributes:
        STRING (str): Represents a string parameter type.
        INT (str): Represents an integer parameter type.
        FLOAT (str): Represents a float parameter type.
        BOOL (str): Represents a boolean parameter type.
        OPTION (str): Represents an option parameter type.
        ARTIFACT (str): Represents an artifact parameter type.
        COLLECTION (str): Represents a collection parameter type.
    """

    STRING = "string"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    OPTION = "option"
    ARTIFACT = "artifact"
    COLLECTION = "collection"


class Arguments:
    """
    A utility class for building command-line arguments based on a given parameter.
    """

    def build(self, parameter) -> Dict[str, Any]:
        """
        Builds command-line arguments based on a given parameter.

        Args:
            parameter: A parameter object containing information about the argument.

        Returns:
            A dictionary containing the arguments for the command-line.
        """
        if not isinstance(parameter.type, Type):
            raise ValueError(
                f"Wrong type declaration for '{parameter.name}' - use enum 'Type'"
            )

        type2type = {
            Type.STRING: str,
            Type.INT: int,
            Type.FLOAT: float,
            Type.BOOL: bool,
        }

        action_map = {
            Type.OPTION: {
                "choices": list(
                    map(
                        lambda o: o.value,
                        parameter.options if parameter.options else [],
                    )
                )
            },
            Type.ARTIFACT: {
                "type": verify_artifact,
                "metavar": "URN",
                "action": ArtifactAction,
            },
            Type.COLLECTION: {
                "type": verify_collection,
                "metavar": "URN",
                "action": CollectionAction,
            },
            Type.BOOL: {
                "action": "store_true",
                "required": False,
            },
        }

        args: Dict[str, Any] = dict(required=True)
        param_type_action = action_map.get(parameter.type)
        if param_type_action:
            args.update(param_type_action)
        else:
            parameter_type = type2type.get(parameter.type)
            if not parameter_type:
                raise ValueError(
                    f"Unsupported type '{parameter.type}' for '{parameter.name}'"
                )
            args["type"] = parameter_type
            args["metavar"] = parameter.type.name.upper()

        if parameter.default:
            args["default"] = parameter.default

        if parameter.description:
            if parameter.default:
                args["help"] = f"{parameter.description} [{parameter.default}]"
            else:
                args["help"] = f"{parameter.description}"

        if parameter.optional:
            args["required"] = not parameter.optional
        # wut???? elif maybe?
        if parameter.constant or parameter.default:
            args["required"] = False

        return args


@dataclass()
class Parameter(JSONWizard):
    """
    Defines a `Service` parameter.

    Attributes:
        name (str): The name of the parameter.
        type (Type): The type of the parameter.
        options (List[Option], optional): The list of options for the parameter. Defaults to None.
        description (str, optional): The description of the parameter. Defaults to None.
        default (Any, optional): The default value of the parameter. Defaults to None.
        unit (str, optional): The unit of the parameter. Defaults to None.
        help (str, optional): The help text for the parameter. Defaults to None.
        optional (bool, optional): Whether the parameter is optional. Defaults to False.
        constant (bool, optional): Whether the parameter is constant. Defaults to False.
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
        self.default = self.to_str(self.default)

    def to_dict(self):
        d = super().to_dict()
        if self.type == Type.BOOL and not self.default:
            d["optional"] = True
        return d

    def to_str(self, value):
        """
        Converts the given value to a string representation.

        Args:
            value: The value to convert.

        Returns:
            The string representation of the value.
        """
        return str(value) if value is not None and not isinstance(value, str) else value


@dataclass
class Workflow(JSONWizard):
    """Defines the workflow associated with a `Service`

    Attributes:
        type (str): The type of the workflow.
    """

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
    image: str = os.getenv("IVCAP_CONTAINER", "@CONTAINER@")
    command: List[str] = field(default_factory=list)
    min_memory: str = None

    def to_dict(self):
        basic = {"command": self.command, "image": self.image}
        if self.min_memory:
            basic["memory"] = {"request": self.min_memory}
        return {"type": "basic", "basic": basic}


@dataclass
class PythonWorkflow(BasicWorkflow):
    """Defines an IVCAP 'Service' workflow consisting of a single python script

    Args:
        image (str): Name of docker image ['IVCAP_CONTAINER', '@CONTAINER@']
        script (str): Path to main python script ['/app/service.py']
        min_memory (int): Min memory requirement in ???
    """

    script: str = "/app/service.py"

    @classmethod
    def def_workflow(cls):
        """
        Creates a new instance of the Workflow class.

        :param cls: The Workflow class.
        :return: A new instance of the Workflow class.
        """
        return cls()

    def to_dict(self):
        service_dict = super().to_dict()
        service_dict["basic"]["command"] = ["python", self.script]
        return service_dict


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
    id: str = os.getenv("IVCAP_SERVICE_ID", "@SERVICE_ID@")
    providerID: str = json_field(
        "provider-id", all=True, default=os.getenv("IVCAP_PROVIDER_ID", "@PROVIDER_ID@")
    )
    accountID: str = json_field(
        "account-id", all=True, default=os.getenv("IVCAP_ACCOUNT_ID", "@ACCOUNT_ID@")
    )
    parameters: List[Parameter] = field(default_factory=list)
    description: str = None
    workflow: Workflow = field(default_factory=PythonWorkflow.def_workflow)

    @classmethod
    def from_file(cls, serviceFile: str) -> None:
        """
        Create a Service object from a YAML file.

        Args:
            serviceFile (str): The path to the YAML file.

        Returns:
            None
        """
        pd = read_yaml_no_dates(serviceFile)
        return cls.from_dict(pd)

    # this function is NOT calling the 'to_dict' of referenced JSONWizard classes
    def to_dict(self):
        """
        Converts the current Service object to a dictionary representation.

        Returns:
            dict: A dictionary representation of the Service object.
        """
        service_dict = super().to_dict()
        service_dict["parameters"] = list(map(lambda p: p.to_dict(), self.parameters))
        service_dict["workflow"] = self.workflow.to_dict()
        return service_dict

    def to_yaml(self) -> str:
        """
        Convert the current object to a YAML string representation.

        :return: A string containing the YAML representation of the object.
        """
        return yaml.dump(self.to_dict(), default_flow_style=False)

    def append_arguments(self, argument_parser: ArgumentParser) -> ArgumentParser:
        """
        Appends arguments to the given ArgumentParser object based on the parameters defined in the service.

        Args:
            ap (ArgumentParser): The ArgumentParser object to which the arguments will be appended.

        Returns:
            ArgumentParser: The updated ArgumentParser object.
        """

        argument_builder = Arguments()
        for parameter in self.parameters:
            if not (parameter.name or parameter.type):
                raise ValueError(
                    f"Service parameter '{parameter}' is missing a name or type"
                )

            if parameter.name.startswith(("cre:", "ivcap:")):
                continue

            try:
                args = argument_builder.build(parameter)
            except ValueError as err:
                raise ValueError("An error occurred: {}".format(str(err))) from err

            argument_parser.add_argument(f"--{parameter.name}", **args)

        return argument_parser
