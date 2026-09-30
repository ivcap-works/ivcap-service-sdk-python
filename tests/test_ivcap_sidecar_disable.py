#
# Copyright (c) 2026 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
"""Tests for `--test-without-sidecar` / sidecar delivery suppression."""

import pytest

import ivcap_service.ivcap as ivcap_mod
from ivcap_service.ivcap import (
    SidecarReporter,
    is_sidecar_delivery_disabled,
    push_result,
    set_result_callback,
    set_sidecar_delivery_disabled,
)
from ivcap_service.types import IvcapResult


@pytest.fixture(autouse=True)
def _reset_sidecar_disabled_flag():
    """Ensure the module-level flag doesn't leak between tests."""
    set_sidecar_delivery_disabled(False)
    yield
    set_sidecar_delivery_disabled(False)


def test_default_sidecar_delivery_enabled():
    assert is_sidecar_delivery_disabled() is False


def test_set_sidecar_delivery_disabled_toggles_flag():
    set_sidecar_delivery_disabled(True)
    assert is_sidecar_delivery_disabled() is True

    set_sidecar_delivery_disabled(False)
    assert is_sidecar_delivery_disabled() is False


def test_push_result_skips_http_when_disabled(monkeypatch: pytest.MonkeyPatch):
    """push_result() must not attempt any HTTP call when sidecar delivery is
    disabled, even if IVCAP_BASE_URL is configured."""

    monkeypatch.setenv("IVCAP_BASE_URL", "http://ivcap.local")
    set_sidecar_delivery_disabled(True)

    called = False

    def _fake_post(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("httpx.post should not have been called")

    monkeypatch.setattr(ivcap_mod.httpx, "post", _fake_post)

    result = IvcapResult(content="hello", content_type="text/plain")
    # Should not raise and should not call httpx.post
    push_result(result, "job-123", None)

    assert called is False


def test_push_result_still_calls_result_callback_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
):
    """Sidecar delivery being disabled must not suppress a locally registered
    result_callback - only actual sidecar HTTP delivery is skipped."""

    monkeypatch.setenv("IVCAP_BASE_URL", "http://ivcap.local")
    set_sidecar_delivery_disabled(True)

    received = []

    def _cbk(result, job_id, authorization):
        received.append((result, job_id, authorization))

    set_result_callback(_cbk)
    try:
        result = IvcapResult(content="hello", content_type="text/plain")
        push_result(result, "job-123", "auth-token")
        assert len(received) == 1
        assert received[0][1] == "job-123"
    finally:
        set_result_callback(None)  # type: ignore[arg-type]


def test_push_result_calls_http_when_not_disabled(monkeypatch: pytest.MonkeyPatch):
    """Sanity check: with the flag off (default), push_result() does attempt
    delivery when IVCAP_BASE_URL is set."""

    monkeypatch.setenv("IVCAP_BASE_URL", "http://ivcap.local")
    set_sidecar_delivery_disabled(False)

    called = False

    class _Resp:
        def raise_for_status(self):
            pass

    def _fake_post(*args, **kwargs):
        nonlocal called
        called = True
        return _Resp()

    monkeypatch.setattr(ivcap_mod.httpx, "post", _fake_post)

    result = IvcapResult(content="hello", content_type="text/plain")
    push_result(result, "job-123", None)

    assert called is True


def test_sidecar_reporter_send_skips_http_when_disabled(monkeypatch: pytest.MonkeyPatch):
    """SidecarReporter._send() must not attempt any HTTP call when sidecar
    delivery is disabled."""

    monkeypatch.setenv("IVCAP_BASE_URL", "http://ivcap.local")
    set_sidecar_delivery_disabled(True)

    called = False

    def _fake_post(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("httpx.post should not have been called")

    monkeypatch.setattr(ivcap_mod.httpx, "post", _fake_post)

    reporter = SidecarReporter("job-123", "auth-token")
    reporter.step_started("my-step", message="starting")

    assert called is False


def test_sidecar_reporter_send_calls_http_when_not_disabled(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("IVCAP_BASE_URL", "http://ivcap.local")
    set_sidecar_delivery_disabled(False)

    called = False

    class _Resp:
        def raise_for_status(self):
            pass

    def _fake_post(*args, **kwargs):
        nonlocal called
        called = True
        return _Resp()

    monkeypatch.setattr(ivcap_mod.httpx, "post", _fake_post)

    reporter = SidecarReporter("job-123", "auth-token")
    reporter.step_started("my-step", message="starting")

    assert called is True
