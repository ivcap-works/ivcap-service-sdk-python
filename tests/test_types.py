#
# Copyright (c) 2026 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
from io import BytesIO

from ivcap_service.events import EventReporter
from ivcap_service.types import BinaryResult, ExecutionError, IvcapResult, JobContext


def test_binary_result_with_bytes():
    """Test BinaryResult with byte content."""
    content = b"binary data"
    result = BinaryResult(content_type="application/octet-stream", content=content)
    assert result.content_type == "application/octet-stream"
    assert result.content == content


def test_binary_result_with_string():
    """Test BinaryResult with string content."""
    content = "text content"
    result = BinaryResult(content_type="text/plain", content=content)
    assert result.content_type == "text/plain"
    assert result.content == content


def test_binary_result_with_file_handle():
    """Test BinaryResult with file handle."""
    file_handle = BytesIO(b"file data")
    result = BinaryResult(content_type="application/pdf", content=file_handle)
    assert result.content_type == "application/pdf"
    assert result.content == file_handle


def test_ivcap_result_defaults():
    """Test IvcapResult with default values."""
    result = IvcapResult(content_type="application/json", content=b'{"key": "value"}')
    assert result.isError is False
    assert result.raw is None
    assert result.content_type == "application/json"


def test_ivcap_result_as_error():
    """Test IvcapResult when marking as error."""
    result = IvcapResult(
        content_type="application/json",
        content=b'{"error": "failed"}',
        isError=True,
        raw={"error": "failed"},
    )
    assert result.isError is True
    assert result.raw == {"error": "failed"}


def test_execution_error_model():
    """Test ExecutionError model validation and serialization."""
    error = ExecutionError(error="Something went wrong", type="ValueError")
    assert error.error == "Something went wrong"
    assert error.type == "ValueError"
    assert error.traceback is None
    assert error.jschema == "urn:ivcap:schema.service.error.1"


def test_execution_error_with_traceback():
    """Test ExecutionError with traceback."""
    tb = "Traceback (most recent call last):\n  File ..., line 1\nValueError: bad value"
    error = ExecutionError(error="Bad value provided", type="ValueError", traceback=tb)
    assert error.traceback == tb


def test_execution_error_serialization():
    """Test ExecutionError serialization includes schema."""
    error = ExecutionError(error="Test error", type="RuntimeError")
    data = error.model_dump(by_alias=True)
    assert data["$schema"] == "urn:ivcap:schema.service.error.1"
    assert data["error"] == "Test error"
    assert data["type"] == "RuntimeError"


def test_job_context_defaults():
    """Test JobContext initialization with defaults."""
    ctx = JobContext()
    assert ctx.job_id is None
    assert ctx.report is None
    assert ctx.job_authorization is None


def test_job_context_with_values():
    """Test JobContext with actual values."""
    report = EventReporter("job-123", "auth-token")
    ctx = JobContext(job_id="job-123", report=report, job_authorization="auth-token")
    assert ctx.job_id == "job-123"
    assert ctx.report == report
    assert ctx.job_authorization == "auth-token"


def test_job_context_ivcap_private_attr():
    """Test JobContext has _ivcap private attribute initialized to None."""
    ctx = JobContext(job_id="job-123")
    # The private attribute should be initialized to None
    assert ctx._ivcap is None
