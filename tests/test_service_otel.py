#
# Copyright (c) 2026 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
import pytest


class DummySpan:
    def __init__(self):
        self.attributes = {}

    def set_attribute(self, k, v):
        self.attributes[k] = v

    def record_exception(self, exc):
        pass

    def set_status(self, status):
        pass


class DummySpanCM:
    def __init__(self, span: DummySpan):
        self.span = span

    def __enter__(self):
        return self.span

    def __exit__(self, exc_type, exc, tb):
        return False


class DummyTracer:
    def __init__(self, span: DummySpan):
        self.span = span

    def start_as_current_span(self, name: str):
        return DummySpanCM(self.span)


def test_job_span_tags_job_id_and_service_id(monkeypatch: pytest.MonkeyPatch):
    """`_job_span()` should tag the span with both `ivcap.job_id` and, when
    available, `ivcap.service_id` (sourced from `IVCAP_SERVICE_ID`)."""

    from ivcap_service import service

    span = DummySpan()
    tracer = DummyTracer(span)

    monkeypatch.setitem(
        __import__("sys").modules,
        "opentelemetry",
        type("otel", (), {"trace": type("trace", (), {"get_tracer": lambda name: tracer})})(),
    )

    with service._job_span("job-123", "urn:ivcap:service:abc") as s:
        assert s is span

    assert span.attributes["ivcap.job_id"] == "job-123"
    assert span.attributes["ivcap.service_id"] == "urn:ivcap:service:abc"


def test_job_span_without_service_id(monkeypatch: pytest.MonkeyPatch):
    """When no service_id is available, only job_id should be tagged."""

    from ivcap_service import service

    span = DummySpan()
    tracer = DummyTracer(span)

    monkeypatch.setitem(
        __import__("sys").modules,
        "opentelemetry",
        type("otel", (), {"trace": type("trace", (), {"get_tracer": lambda name: tracer})})(),
    )

    with service._job_span("job-123") as s:
        assert s is span

    assert span.attributes["ivcap.job_id"] == "job-123"
    assert "ivcap.service_id" not in span.attributes


def test_get_service_id_reads_env(monkeypatch: pytest.MonkeyPatch):
    from ivcap_service.service import _get_service_id

    monkeypatch.delenv("IVCAP_SERVICE_ID", raising=False)
    assert _get_service_id() is None

    monkeypatch.setenv("IVCAP_SERVICE_ID", "urn:ivcap:service:xyz")
    assert _get_service_id() == "urn:ivcap:service:xyz"
