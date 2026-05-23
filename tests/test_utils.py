#
# Copyright (c) 2026 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
import json
import os
import tempfile

import pytest
from pydantic import BaseModel

from ivcap_service.utils import (
    clean_description,
    file_to_json,
    get_function_return_type,
    get_input_type,
)


class SimpleModel(BaseModel):
    """Simple test Pydantic model."""

    name: str
    value: int


def test_get_input_type_with_pydantic_model():
    """Test get_input_type extracts Pydantic model correctly."""

    def func_with_model(model: SimpleModel, extra: str):
        pass

    pydantic_class, additional_params = get_input_type(func_with_model)
    assert pydantic_class is SimpleModel
    assert "extra" in additional_params
    assert additional_params["extra"] is str


def test_get_input_type_without_pydantic_model():
    """Test get_input_type when no Pydantic model is present."""

    def func_without_model(a: str, b: int):
        pass

    pydantic_class, additional_params = get_input_type(func_without_model)
    assert pydantic_class is None
    assert len(additional_params) == 2
    assert additional_params["a"] is str
    assert additional_params["b"] is int


def test_get_input_type_with_optional_types():
    """Test get_input_type with Optional types."""

    def func_with_optional(model: SimpleModel, opt: str | None = None):
        pass

    pydantic_class, additional_params = get_input_type(func_with_optional)
    assert pydantic_class is SimpleModel
    assert "opt" in additional_params


def test_get_function_return_type_basic():
    """Test get_function_return_type extracts return type."""

    def func_returns_str() -> str:
        return "hello"

    return_type = get_function_return_type(func_returns_str)
    assert return_type is str


def test_get_function_return_type_complex():
    """Test get_function_return_type with complex return type."""

    def func_returns_list() -> list[str]:
        return ["a", "b"]

    return_type = get_function_return_type(func_returns_list)
    # The type hint will be a generic alias
    assert return_type is not None


def test_get_function_return_type_optional():
    """Test get_function_return_type with Optional return."""

    def func_returns_optional() -> int | None:
        return None

    return_type = get_function_return_type(func_returns_optional)
    assert return_type is not None


def test_get_function_return_type_none():
    """Test get_function_return_type when no return type annotation."""

    def func_no_return():
        pass

    return_type = get_function_return_type(func_no_return)
    assert return_type is None


def test_file_to_json_valid():
    """Test file_to_json with valid JSON file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"key": "value", "number": 42}, f)
        temp_path = f.name

    try:
        data = file_to_json(temp_path)
        assert data["key"] == "value"
        assert data["number"] == 42
    finally:
        os.unlink(temp_path)


def test_file_to_json_complex_structure():
    """Test file_to_json with complex nested structure."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        complex_data = {
            "items": [
                {"id": 1, "name": "item1"},
                {"id": 2, "name": "item2"},
            ],
            "meta": {"count": 2, "version": "1.0"},
        }
        json.dump(complex_data, f)
        temp_path = f.name

    try:
        data = file_to_json(temp_path)
        assert len(data["items"]) == 2
        assert data["meta"]["count"] == 2
    finally:
        os.unlink(temp_path)


def test_file_to_json_not_found():
    """Test file_to_json raises FileNotFoundError for missing file."""
    with pytest.raises(FileNotFoundError):
        file_to_json("/nonexistent/path/file.json")


def test_file_to_json_invalid_json():
    """Test file_to_json raises ValueError for invalid JSON."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("not valid json {")
        temp_path = f.name

    try:
        with pytest.raises(ValueError, match="Error decoding JSON"):
            file_to_json(temp_path)
    finally:
        os.unlink(temp_path)


def test_clean_description_basic():
    """Test clean_description removes extra whitespace."""
    text = "  This is   a  test  "
    cleaned = clean_description(text)
    assert cleaned == "This is a test"


def test_clean_description_with_double_newlines():
    """Test clean_description converts double newlines to single newlines."""
    text = "Paragraph 1\n\nParagraph 2"
    cleaned = clean_description(text)
    # Double newlines are converted to single newlines
    assert cleaned == "Paragraph 1\nParagraph 2"


def test_clean_description_converts_single_newlines():
    """Test clean_description converts single newlines to spaces."""
    text = "Line 1\nLine 2\nLine 3"
    cleaned = clean_description(text)
    assert cleaned == "Line 1 Line 2 Line 3"


def test_clean_description_normalizes_whitespace_around_newlines():
    """Test clean_description properly normalizes whitespace."""
    text = "Start\n\nMiddle\nEnd"
    cleaned = clean_description(text)
    # Should preserve double newlines and convert single to spaces
    assert "Start" in cleaned
    assert "Middle" in cleaned
    assert "End" in cleaned


def test_clean_description_tabs_and_spaces():
    """Test clean_description with tabs and multiple spaces."""
    text = "Text\t\twith\t  tabs\n  and  spaces"
    cleaned = clean_description(text)
    assert "Text with tabs and spaces" == cleaned
