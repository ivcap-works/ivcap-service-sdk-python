import pytest
import math
from argparse import ArgumentParser
from ivcap_sdk_service.service import (
    Service,
    Parameter,
    PythonWorkflow,
    Type,
    Option,
    Arguments,
)

from ivcap_sdk_service.verifiers import CollectionAction


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


def test_build_argument_with_unsupported_type():
    """
    Test that an exception is raised when a parameter is defined with a wrong type declaration.
    """
    parameter = Parameter(
        name="A name",
        type=bytes,
        default=100,
        optional=True,
    )

    arguments = Arguments()
    with pytest.raises(
        ValueError, match=f"Unsupported type '{parameter.type}' for '{parameter.name}'"
    ):
        arguments.build(parameter)
