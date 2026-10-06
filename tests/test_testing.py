#
# Copyright (c) 2026 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
import pytest

from ivcap_service.testing import file_to_http_response


def test_file_to_http_response_defaults(tmp_path):
    file_path = tmp_path / "data.bin"
    content = b"hello world"
    file_path.write_bytes(content)

    response = file_to_http_response(str(file_path))

    assert response.status_code == 200
    assert response.content == content
    assert response.headers["content-type"] == "application/octet-stream"
    assert response.headers["content-length"] == str(len(content))


def test_file_to_http_response_custom_status_and_headers(tmp_path):
    file_path = tmp_path / "data.json"
    content = b'{"ok": true}'
    file_path.write_bytes(content)

    response = file_to_http_response(
        str(file_path),
        headers={"Content-Type": "application/json", "X-Custom": "yes"},
        status_code=201,
    )

    assert response.status_code == 201
    assert response.content == content
    assert response.headers["content-type"] == "application/json"
    assert response.headers["x-custom"] == "yes"


def test_file_to_http_response_missing_file():
    with pytest.raises(FileNotFoundError):
        file_to_http_response("/nonexistent/path/file.bin")


def test_file_to_http_response_directory_not_file(tmp_path):
    with pytest.raises(ValueError, match="Not a file"):
        file_to_http_response(str(tmp_path))


def test_file_to_http_response_invalid_status_code_too_low(tmp_path):
    file_path = tmp_path / "data.bin"
    file_path.write_bytes(b"x")

    with pytest.raises(ValueError, match="Invalid HTTP status code"):
        file_to_http_response(str(file_path), status_code=99)


def test_file_to_http_response_invalid_status_code_too_high(tmp_path):
    file_path = tmp_path / "data.bin"
    file_path.write_bytes(b"x")

    with pytest.raises(ValueError, match="Invalid HTTP status code"):
        file_to_http_response(str(file_path), status_code=600)


def test_file_to_http_response_empty_file(tmp_path):
    file_path = tmp_path / "empty.bin"
    file_path.write_bytes(b"")

    response = file_to_http_response(str(file_path))

    assert response.content == b""
    assert response.headers["content-length"] == "0"
