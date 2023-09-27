import pytest
import math
from argparse import ArgumentParser
from ivcap_sdk_service.service import (
    Service,
    Parameter,
    BasicWorkflow,
    PythonWorkflow,
    Type,
    Option,
    Arguments,
)

from ivcap_sdk_service.verifiers import CollectionAction

# ....................................................#
# ........ This section tests the Service class.......#
# ....................................................#


def test_append_all_arguments():
    service = Service(
        description="Unit test service with all parameter types",
        name="unit-test-service",
        parameters=[
            # Parameter(
            #     name="test_artifact",
            #     description="input file",
            #     type=Type.ARTIFACT,
            #     optional=False,
            # ),
            Parameter(
                name="test_integer",
                description="number of things to do",
                type=Type.INT,
                default=100,
                optional=True,
            ),
            Parameter(
                name="test_string",
                description="starting background color (hex)",
                type=Type.STRING,
                default="the default value",
                optional=True,
            ),
            Parameter(
                name="test_float",
                description="temperature in degrees Celsius",
                type=Type.FLOAT,
                default=23.23,
                optional=True,
            ),
            Parameter(
                name="test_bool",
                description="is the thing on?",
                type=Type.BOOL,
                default=False,
                optional=True,
            ),
            Parameter(
                name="test_option",
                description="a list of options",
                type=Type.OPTION,
                options=[
                    Option(value="fp32"),
                    Option(value="fp16"),
                    Option(value="int8"),
                ],
                default="fp32",
                optional=True,
            ),
            Parameter(
                name="test_collection",
                description="use the min, max, or average",
                type=Type.COLLECTION,
                optional=True,
            ),
        ],
        workflow=PythonWorkflow(script="/primitive/service.py", min_memory="2Gi"),
    )

    argument_parser = ArgumentParser(description=service.description)
    service.append_arguments(argument_parser)
    pargs = argument_parser.parse_args([])

    assert pargs.test_integer == 100
    assert pargs.test_string == "the default value"
    assert math.isclose(pargs.test_float, 23.23, rel_tol=1e-9, abs_tol=1e-12)
    assert pargs.test_bool == "False"
    assert pargs.test_option == "fp32"
    assert pargs.test_collection is None


def test_append_no_arguments():
    service = Service(
        description="Unit test service with no parameters",
        name="unit-test-service",
        parameters=[],
        workflow=PythonWorkflow(script="/primitive/service.py", min_memory="2Gi"),
    )

    argument_parser = ArgumentParser(description=service.description)
    service.append_arguments(argument_parser)
    pargs = argument_parser.parse_args([])

    assert vars(pargs) == {}


def test_undefined_parameter_name_exception():
    service = Service(
        description="Unit test service with no parameters",
        name="unit-test-service",
        parameters=[
            Parameter(
                name="",
                description="number of things to do",
                type=Type.INT,
                default=100,
                optional=True,
            ),
        ],
        workflow=PythonWorkflow(script="/primitive/service.py", min_memory="2Gi"),
    )

    argument_parser = ArgumentParser(description=service.description)

    with pytest.raises(ValueError):
        service.append_arguments(argument_parser)


def test_append_argument_undefined_parameter_type_exception():
    service = Service(
        description="Unit test service with no parameters",
        name="unit-test-service",
        parameters=[
            Parameter(
                name="A name",
                description="number of things to do",
                type=None,
                default=100,
                optional=True,
            ),
        ],
        workflow=PythonWorkflow(script="/primitive/service.py", min_memory="2Gi"),
    )

    argument_parser = ArgumentParser(description=service.description)

    with pytest.raises(ValueError):
        service.append_arguments(argument_parser)


def test_append_arguments_ignores_special_names():
    service = Service(
        description="Unit test service with no parameters",
        name="unit-test-service",
        parameters=[
            Parameter(
                name="cre:ate",
                description="number of things to do",
                type=Type.INT,
                default=100,
                optional=True,
            ),
            Parameter(
                name="ivcap:client",
                description="number of things to do",
                type=Type.INT,
                default=100,
                optional=True,
            ),
        ],
        workflow=PythonWorkflow(script="/primitive/service.py", min_memory="2Gi"),
    )

    argument_parser = ArgumentParser(description=service.description)
    service.append_arguments(argument_parser)
    pargs = argument_parser.parse_args([])

    assert vars(pargs) == {}


# ....................................................#
# ....... This section tests the Arguments class......#
# ....................................................#


def test_build_integer_argument():
    parameter = Parameter(
        name="test_integer",
        description="number of things to do",
        type=Type.INT,
        default=100,
        optional=True,
    )

    arguments = Arguments()
    args = arguments.build(parameter)

    assert "required" in args
    assert "type" in args
    assert "metavar" in args
    assert "default" in args
    assert "help" in args

    assert args["required"] is False
    assert args["type"] == int
    assert args["metavar"] == "INT"
    assert args["default"] == "100"
    assert args["help"] == "number of things to do [100]"


def test_build_string_argument():
    parameter = Parameter(
        name="test_string",
        description="starting background color (hex)",
        type=Type.STRING,
        default="the default value",
        optional=True,
    )

    arguments = Arguments()
    args = arguments.build(parameter)

    assert "required" in args
    assert "type" in args
    assert "metavar" in args
    assert "default" in args
    assert "help" in args

    assert args["required"] is False
    assert args["type"] == str
    assert args["metavar"] == "STRING"
    assert args["default"] == "the default value"
    assert args["help"] == "starting background color (hex) [the default value]"


def test_build_bool_argument():
    parameter = Parameter(
        name="test_bool",
        description="is the thing on?",
        type=Type.BOOL,
        default=False,
        optional=True,
    )

    arguments = Arguments()
    args = arguments.build(parameter)

    assert "required" in args
    assert "action" in args
    assert "default" in args
    assert "help" in args

    assert args["required"] is False
    assert args["action"] == "store_true"
    assert args["default"] == "False"
    assert args["help"] == "is the thing on? [False]"


def test_build_float_argument():
    parameter = Parameter(
        name="test_float",
        description="temperature in degrees Celsius",
        type=Type.FLOAT,
        default=23.23,
        optional=True,
    )

    arguments = Arguments()
    args = arguments.build(parameter)

    assert "required" in args
    assert "type" in args
    assert "metavar" in args
    assert "default" in args
    assert "help" in args

    assert args["required"] is False
    assert args["type"] == float
    assert args["metavar"] == "FLOAT"
    assert args["default"] == "23.23"
    assert args["help"] == "temperature in degrees Celsius [23.23]"


def test_build_option_argument():
    parameter = Parameter(
        name="test_option",
        description="a list of options",
        type=Type.OPTION,
        options=[
            Option(value="fp32"),
            Option(value="fp16"),
            Option(value="int8"),
        ],
        default="fp32",
        optional=True,
    )

    arguments = Arguments()
    args = arguments.build(parameter)

    assert "required" in args
    assert "choices" in args
    assert "default" in args
    assert "help" in args

    assert args["required"] is False
    assert args["choices"] == ["fp32", "fp16", "int8"]
    assert args["default"] == "fp32"
    assert args["help"] == "a list of options [fp32]"


def test_build_collection_argument():
    parameter = Parameter(
        name="test_collection",
        description="use the min, max, or average",
        type=Type.COLLECTION,
        optional=True,
    )

    arguments = Arguments()
    args = arguments.build(parameter)

    assert "required" in args
    assert "type" in args
    assert "metavar" in args
    assert "action" in args
    assert "help" in args

    assert args["required"] is False
    assert callable(args["type"])
    assert args["metavar"] == "URN"
    assert isinstance(args["action"], type(CollectionAction))
    assert args["help"] == "use the min, max, or average"


def test_build_argument_with_wrong_type_declaration():
    """
    Test that an exception is raised when a parameter is defined with a wrong type declaration.
    """
    parameter = Parameter(
        name="A name",
        type=None,
        default=100,
        optional=True,
    )

    arguments = Arguments()
    with pytest.raises(
        ValueError,
        match=f"Wrong type declaration for '{parameter.name}' - use enum 'Type'",
    ):
        arguments.build(parameter)


#
# NOTE: This test is commented out as it is not *currently* possible to get to a scenario
#       where we have an unsupported type. The parameter type is checked when the service
#       is created. The only way to get to this scenario is to add a custome type to
#       class `Type` and forget to add it to the `action_map` in the `Arguments` class.
# def test_build_argument_with_unsupported_type():
#     """
#     Test that an exception is raised when a parameter is defined with a wrong type declaration.
#     """
#     parameter = Parameter(
#         name="A name",
#         type=None,
#         default=100,
#         optional=True,
#     )
#
#     arguments = Arguments()
#     with pytest.raises(
#         ValueError, match=f"Unsupported type '{parameter.type}' for '{parameter.name}'"
#     ):
#         arguments.build(parameter)


# ....................................................#
# ....... This section tests the Parameter class......#
# ....................................................#
def test_parameter_creation():
    param = Parameter(name="test_param", type=Type.STRING, description="Test parameter")
    assert param.name == "test_param"
    assert param.type == Type.STRING
    assert param.description == "Test parameter"
    assert param.default is None
    assert param.unit is None
    assert param.help is None
    assert param.optional is False
    assert param.constant is False


def test_parameter_creation_with_options():
    options = [Option(value="option1"), Option(value="option2")]
    param = Parameter(name="test_param", type=Type.OPTION, options=options)
    assert param.name == "test_param"
    assert param.type == Type.OPTION
    assert param.options == options
    assert param.description is None
    assert param.default is None
    assert param.unit is None
    assert param.help is None
    assert param.optional is False
    assert param.constant is False


def test_parameter_to_dict():
    param = Parameter(
        name="test_param", type=Type.BOOL, description="Test parameter", default=False
    )
    param_dict = param.to_dict()
    assert param_dict["name"] == "test_param"
    assert param_dict["type"] == "bool"
    assert param_dict["description"] == "Test parameter"
    assert param_dict["default"] == "False"

    assert "constant" not in param_dict
    assert "optional" not in param_dict
    assert "unit" not in param_dict
    assert "help" not in param_dict


def test_parameter_to_str():
    param = Parameter(name="test_param", type=Type.STRING, default=123)
    assert param.to_str(123) == "123"
    assert param.to_str("test") == "test"
    assert param.to_str(None) is None


# ....................................................#
# ..... This section tests the BasicWorkflow class....#
# ....................................................#
def test_basic_workflow():
    workflow = BasicWorkflow(command=["/bin/bash"], min_memory="1Gi")
    assert workflow.type == "basic"
    assert workflow.image == "@CONTAINER@"
    assert workflow.command == ["/bin/bash"]
    assert workflow.min_memory == "1Gi"
    assert workflow.to_dict() == {
        "type": "basic",
        "basic": {
            "command": ["/bin/bash"],
            "image": "@CONTAINER@",
            "memory": {"request": "1Gi"},
        },
    }


# ....................................................#
# .... This section tests the PythonWorkflow class....#
# ....................................................#
def test_python_workflow():
    workflow = PythonWorkflow(script="/primitive/service.py", min_memory="2Gi")
    assert workflow.type == "basic"
    assert workflow.image == "@CONTAINER@"
    assert workflow.script == "/primitive/service.py"
    assert workflow.min_memory == "2Gi"
    print(workflow.to_dict())
    assert workflow.to_dict() == {
        "type": "basic",
        "basic": {
            "command": ["python", "/primitive/service.py"],
            "image": "@CONTAINER@",
            "memory": {"request": "2Gi"},
        },
    }
