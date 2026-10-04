#
# Copyright (c) 2026 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
"""Tests for unconditional W3C trace context propagation on outbound requests.

`_modify_request()` is applied to every outbound `requests`/`httpx` call
(via `set_context()`), regardless of whether OTEL HTTP auto-instrumentation
(`RequestsInstrumentor`/`HTTPXClientInstrumentor`, see `otel_instrument()`)
is enabled. These tests ensure the current trace context (`traceparent`) is
still propagated onto outbound requests - routed through the sidecar/proxy
or not - even when that auto-instrumentation is off.
"""

import logging

import pytest


@pytest.fixture(autouse=True)
def _reset_tracer_provider():
    """Reset the global TracerProvider around each test.

    `opentelemetry.trace._TRACER_PROVIDER` is a module-level singleton that
    can only be set once per process; we reset it directly after each test
    so we don't leak our test provider into other test modules (mirrors the
    pattern used in `tests/test_openobserve_traces.py`).
    """
    from opentelemetry import trace
    from opentelemetry.util._once import Once

    yield

    trace._TRACER_PROVIDER = None  # type: ignore[attr-defined]
    trace._TRACER_PROVIDER_SET_ONCE = Once()  # type: ignore[attr-defined]


def test_modify_request_injects_traceparent_header():
    """`_modify_request()` should add a `traceparent` header using the
    currently active OTEL span context, independent of `otel_instrument()`.
    """
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider

    # Install a real SDK TracerProvider so spans actually carry a valid
    # SpanContext (NoOp spans have an invalid context and won't propagate).
    provider = TracerProvider()
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer("test.context_trace_propagation")

    from ivcap_service.context import _modify_request

    class FakeRequest:
        def __init__(self, url: str):
            self.url = url
            self.headers: dict[str, str] = {}

    logger = logging.getLogger("test.context_trace_propagation")

    with tracer.start_as_current_span("test-span"):
        req = FakeRequest("https://example.ivcap.net/some/path")
        _modify_request(req, None, logger)

    assert "traceparent" in req.headers


def test_modify_request_skips_trace_context_for_otel_endpoint(monkeypatch):
    """Trace context must not be injected into calls made to the OTEL
    collector endpoint itself (to avoid self-referential export traces)."""
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider

    provider = TracerProvider()
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer("test.context_trace_propagation")

    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318")

    from ivcap_service.context import _modify_request

    class FakeRequest:
        def __init__(self, url: str):
            self.url = url
            self.headers: dict[str, str] = {}

    logger = logging.getLogger("test.context_trace_propagation")

    with tracer.start_as_current_span("test-span"):
        req = FakeRequest("http://collector:4318/v1/traces")
        _modify_request(req, None, logger)

    assert "traceparent" not in req.headers


def test_inject_trace_context_never_raises_without_opentelemetry(monkeypatch):
    """Even if `opentelemetry.propagate` import/injection fails, this must
    be a silent no-op (best-effort) rather than breaking the request."""
    import ivcap_service.context as context_mod

    def _boom(headers):
        raise RuntimeError("boom")

    class FakePropagate:
        inject = staticmethod(_boom)

    monkeypatch.setitem(
        __import__("sys").modules, "opentelemetry.propagate", FakePropagate()
    )

    logger = logging.getLogger("test.context_trace_propagation")
    headers: dict[str, str] = {}
    # Should not raise.
    context_mod._inject_trace_context("https://example.ivcap.net/x", headers, logger)
    assert headers == {}
