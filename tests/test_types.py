#
# Copyright (c) 2026 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
import json
from io import BytesIO, StringIO
from typing import Any
from unittest.mock import MagicMock

import pytest

from ivcap_service.events import EventReporter
from ivcap_service.types import BinaryResult, ExecutionError, IvcapResult, JobContext

# 'openai' is an optional dependency of ivcap_service (only required for
# 'JobContext.llm_client()'); skip just the tests that need it rather than
# the whole module when it isn't installed.
openai = pytest.importorskip("openai")


def create_job(ctxt: JobContext, service_id: str, props: dict[str, Any]) -> Any:
    """Create an IVCAP job for 'service_id' with the given 'props' using the
    IVCAP client exposed via the job context's `.ivcap` property.

    This mirrors the recommended usage pattern documented in AGENTS.md:
    look up the target service via `ctxt.ivcap.get_service(...)` and then
    submit a job request for it with `service.request_job(...)`.
    """
    service = ctxt.ivcap.get_service(service_id)
    return service.request_job(StringIO(json.dumps(props)))


SELF_SERVICE_ID = "urn:ivcap:service:self-echo"


def echo_job(ctxt: JobContext, props: dict[str, Any], depth: int) -> dict[str, Any]:
    """A toy 'worker function' that echoes 'props' back.

    If 'depth' is greater than 0, it recursively invokes *itself* as a
    service (via `create_job`) with 'depth' decremented by one, and returns
    whatever that nested job ultimately echoes back. Once 'depth' reaches 0
    it stops recursing and simply returns 'props' unchanged - i.e. the
    innermost call is the one that actually "echoes".
    """
    if depth <= 0:
        return props

    child_props = {**props, "depth": depth - 1}
    job = create_job(ctxt, SELF_SERVICE_ID, child_props)
    return job.result


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
    """Test JobContext initialization with only required fields; job_authorization defaults to None."""
    report = EventReporter("job-123", "")
    ctx = JobContext(job_id="job-123", report=report)
    assert ctx.job_id == "job-123"
    assert ctx.report is report
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
    report = EventReporter("job-123", "")
    ctx = JobContext(job_id="job-123", report=report)
    # The private attribute should be initialized to None
    assert ctx._ivcap is None


def test_llm_client_litellm_proxy_takes_precedence(monkeypatch):
    """LITELLM_PROXY wins over plain OPENAI_* env vars."""
    monkeypatch.setenv("LITELLM_PROXY", "http://localhost:4000")
    monkeypatch.setenv("OPENAI_API_KEY", "env-key")

    report = EventReporter("job-123", "")
    ctx = JobContext(job_id="job-123", report=report)
    client = ctx.llm_client()

    assert str(client.base_url).rstrip("/") == "http://localhost:4000/v1"
    assert client.api_key == "not-needed"


def test_llm_client_uses_openai_env_vars_without_proxy(monkeypatch):
    """Without LITELLM_PROXY, a plain openai.OpenAI() reads OPENAI_* env vars."""
    monkeypatch.delenv("LITELLM_PROXY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "env-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://env.example.com")

    report = EventReporter("job-123", "")
    ctx = JobContext(job_id="job-123", report=report)
    client = ctx.llm_client()

    assert client.api_key == "env-key"
    assert str(client.base_url).rstrip("/") == "https://env.example.com"


def test_llm_client_kwargs_take_precedence_over_litellm_proxy(monkeypatch):
    """Explicit kwargs win over the LITELLM_PROXY-derived defaults."""
    monkeypatch.setenv("LITELLM_PROXY", "http://localhost:4000")

    report = EventReporter("job-123", "")
    ctx = JobContext(job_id="job-123", report=report)
    client = ctx.llm_client(api_key="explicit-key")

    assert client.api_key == "explicit-key"


def test_llm_client_falls_back_to_api_key_file(monkeypatch, tmp_path):
    """When OPENAI_API_KEY isn't set, the api_key file is read as a fallback."""
    import ivcap_service.types as types_module

    key_file = tmp_path / "api_key"
    key_file.write_text("  file-key  \n")

    monkeypatch.delenv("LITELLM_PROXY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(types_module, "_OPENAI_API_KEY_FILE", str(key_file))

    report = EventReporter("job-123", "")
    ctx = JobContext(job_id="job-123", report=report)
    client = ctx.llm_client()

    assert client.api_key == "file-key"


def test_llm_client_env_var_wins_over_api_key_file(monkeypatch, tmp_path):
    """OPENAI_API_KEY takes precedence over the api_key file fallback."""
    import ivcap_service.types as types_module

    key_file = tmp_path / "api_key"
    key_file.write_text("file-key\n")

    monkeypatch.delenv("LITELLM_PROXY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "env-key")
    monkeypatch.setattr(types_module, "_OPENAI_API_KEY_FILE", str(key_file))

    report = EventReporter("job-123", "")
    ctx = JobContext(job_id="job-123", report=report)
    client = ctx.llm_client()

    assert client.api_key == "env-key"


def test_llm_client_raises_when_no_api_key_found(monkeypatch, tmp_path):
    """No kwarg, no OPENAI_API_KEY, no api_key file -> a clear RuntimeError."""
    import ivcap_service.types as types_module

    monkeypatch.delenv("LITELLM_PROXY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        types_module, "_OPENAI_API_KEY_FILE", str(tmp_path / "does-not-exist")
    )

    report = EventReporter("job-123", "")
    ctx = JobContext(job_id="job-123", report=report)

    with pytest.raises(RuntimeError, match="No OpenAI API key found"):
        ctx.llm_client()


def test_create_job():
    """Test creating an IVCAP job for a given service_id/props via ctxt.ivcap.

    Uses a mocked IVCAP client (injected into the JobContext's private
    `_ivcap` attribute) so no real network call is made. Verifies that
    `ctxt.ivcap.get_service(service_id)` is used to look up the service and
    that `service.request_job(...)` is invoked with the supplied props.
    """
    service_id = "urn:ivcap:service:1234"
    props: dict[str, Any] = {"param1": "value1", "param2": 42}

    mock_job = MagicMock(name="Job")
    mock_service = MagicMock(name="Service")
    mock_service.request_job.return_value = mock_job
    mock_ivcap = MagicMock(name="IVCAP")
    mock_ivcap.get_service.return_value = mock_service

    report = EventReporter("job-123", "")
    ctx = JobContext(job_id="job-123", report=report)
    ctx._ivcap = mock_ivcap  # bypass lazy IVCAP() construction

    job = create_job(ctx, service_id, props)

    mock_ivcap.get_service.assert_called_once_with(service_id)
    assert mock_service.request_job.call_count == 1
    (sent_arg,), _ = mock_service.request_job.call_args
    assert json.load(sent_arg) == props
    assert job is mock_job


def test_create_job_recursive_echo():
    """Test the service recursively calling itself (via create_job) to echo.

    Simulates `echo_job` invoking itself as a downstream IVCAP service
    (`ctxt.ivcap.get_service(SELF_SERVICE_ID).request_job(...)`) a fixed
    number of times, with each nested call reducing 'depth' by one, until
    'depth' reaches 0 - at which point the innermost call simply echoes
    'props' back unchanged. The mocked `request_job` re-enters `echo_job`
    synchronously (standing in for the platform actually running the
    recursive job) so no real network/service calls are made.
    """
    report = EventReporter("job-123", "")
    mock_ivcap = MagicMock(name="IVCAP")
    mock_service = MagicMock(name="Service")
    mock_ivcap.get_service.return_value = mock_service

    call_count = 0

    def fake_request_job(data):
        nonlocal call_count
        call_count += 1
        sent_props = json.load(data)
        child_ctx = JobContext(job_id=f"job-{call_count}", report=report)
        child_ctx._ivcap = mock_ivcap
        result = echo_job(child_ctx, sent_props, sent_props["depth"])
        mock_job = MagicMock(name="Job")
        mock_job.result = result
        return mock_job

    mock_service.request_job.side_effect = fake_request_job

    ctx = JobContext(job_id="job-0", report=report)
    ctx._ivcap = mock_ivcap

    props = {"msg": "hello"}
    result = echo_job(ctx, props, depth=3)

    assert result == {"msg": "hello", "depth": 0}
    assert call_count == 3
    assert mock_ivcap.get_service.call_count == 3
    mock_ivcap.get_service.assert_called_with(SELF_SERVICE_ID)
