#
# Copyright (c) 2025 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
import inspect
import json
import os
import re
from typing import Optional, Type, Callable, TypeVar, Any, get_type_hints, Union, Dict, Tuple

from pydantic import BaseModel, HttpUrl

def get_version():
    return "???"

def _get_input_type(func: Callable) -> Tuple[Optional[Type[BaseModel]], Dict[str, Any]]:
    """Gets the input type of a function.

    Args:
        func: The function to get the input type for.

    Returns:
        A tuple containing:
        - The first function parameter which is a derived class of a pydantic BaseModel, or None if no such parameter exists.
        - A dictionary of all additional parameters, where the key is the parameter name and the value is the type.
    """
    signature = inspect.signature(func)
    type_hints = get_type_hints(func)

    # Get the Pydantic model class
    pydantic_model_class = None
    pydantic_param_name = None
    for param_name, param in signature.parameters.items():
        if hasattr(param.annotation, '__mro__') and BaseModel in param.annotation.__mro__:
            pydantic_model_class = param.annotation
            pydantic_param_name = param_name
            break

    # Get all additional parameters
    additional_params = {}
    for param_name, param in signature.parameters.items():
        if param_name != pydantic_param_name:
            param_type = type_hints.get(param_name, Any)
            additional_params[param_name] = param_type

    return pydantic_model_class, additional_params

def _get_function_return_type(func):
    """Extracts the return type from a function."""
    type_hints = get_type_hints(func)
    # param_types = {k: v for k, v in type_hints.items() if k != 'return'}
    return_type = type_hints.get('return')
    # return param_types, return_type
    return return_type

def file_to_json(file_path: str) -> Dict[str, Any]:
    """
    Reads a file, attempts to parse it as JSON, and returns the content.

    Args:
        file_path: The path to the file to read.

    Returns:
        A dictionary containing the parsed JSON content.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not a valid JSON file.
        IOError: If there is an error reading the file.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Error finding file: {file_path}: {e}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Error decoding JSON from file: {file_path}: {e}")
    except Exception as e:
        raise IOError(f"Error reading file: {file_path}: {e}")
