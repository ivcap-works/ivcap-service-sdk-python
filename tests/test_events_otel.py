#
# Copyright (c) 2026 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
import pytest


class DummySpan:
    def __init__(self):
        self.attributes = {}
        self.status = None
        self.exceptions = []

    def set_attribute(self, k, v):
        self.attributes[k] = v

    def set_status(self, status):
        self.status = status

    def record_exception(self, exc: Exception):
        self.exceptions.append(str(exc))


class DummySpanCM:
    def __init__(self, span: DummySpan):
        self.span = span
        self.exited = False

    def __enter__(self):
        return self.span

    def __exit__(self, exc_type, exc, tb):
        self.exited = True
        return False


class DummyTracer:
    def __init__(self, span: DummySpan):
        self.span = span
        self.last_name = None

    def start_as_current_span(self, name: str):
        self.last_name = name
        return DummySpanCM(self.span)


def test_event_context_creates_child_span(monkeypatch: pytest.MonkeyPatch):
    """EventReporter.step() should create a child span and close it when leaving."""

    from ivcap_service import events

    span = DummySpan()
    tracer = DummyTracer(span)

    def _get_tracer(name: str):
        return tracer

    # Patch opentelemetry.trace.get_tracer used inside EventContext.
    monkeypatch.setattr(events, "trace", None, raising=False)
    monkeypatch.setitem(
        __import__("sys").modules,
        "opentelemetry",
        type("otel", (), {"trace": type("trace", (), {"get_tracer": _get_tracer})})(),
    )

    r = events.EventReporter("job-123", None)
    with r.step("my-step") as _ctxt:
        pass

    assert tracer.last_name == "ivcap.event:my-step"
    assert span.attributes["ivcap.job_id"] == "job-123"
    assert span.attributes["ivcap.event_name"] == "my-step"


def test_event_context_tags_service_id(monkeypatch: pytest.MonkeyPatch):
    """EventReporter.step() should also tag `ivcap.service_id` when the
    IVCAP_SERVICE_ID env var is set."""

    from ivcap_service import events

    span = DummySpan()
    tracer = DummyTracer(span)

    def _get_tracer(name: str):
        return tracer

    monkeypatch.setattr(events, "trace", None, raising=False)
    monkeypatch.setitem(
        __import__("sys").modules,
        "opentelemetry",
        type("otel", (), {"trace": type("trace", (), {"get_tracer": _get_tracer})})(),
    )
    monkeypatch.setenv("IVCAP_SERVICE_ID", "urn:ivcap:service:abc")

    r = events.EventReporter("job-123", None)
    with r.step("my-step") as _ctxt:
        pass

    assert span.attributes["ivcap.service_id"] == "urn:ivcap:service:abc"


def test_step_kwargs_are_set_as_span_attributes(monkeypatch: pytest.MonkeyPatch):
    """Extra kwargs passed to report.step(...) must be set as
    `ivcap.event.<key>` span attributes (best-effort, primitive types only),
    in addition to being included in the emitted StepStartEvent."""

    from ivcap_service import events

    span = DummySpan()
    tracer = DummyTracer(span)

    def _get_tracer(name: str):
        return tracer

    monkeypatch.setattr(events, "trace", None, raising=False)
    monkeypatch.setitem(
        __import__("sys").modules,
        "opentelemetry",
        type("otel", (), {"trace": type("trace", (), {"get_tracer": _get_tracer})})(),
    )

    r = events.EventReporter("job-123", None)
    with r.step(
        "consume_compute",
        "Consuming CPU for 2 seconds at 60%",
        duration_seconds=2,
        target_cpu_percent=60,
    ) as _ctxt:
        pass

    assert span.attributes["ivcap.event.duration_seconds"] == 2
    assert span.attributes["ivcap.event.target_cpu_percent"] == 60
    assert span.attributes["ivcap.event.message"] == "Consuming CPU for 2 seconds at 60%"


def test_finished_kwargs_are_set_as_span_attributes(monkeypatch: pytest.MonkeyPatch):
    """Extra kwargs passed to ectxt.finished(...) must also be set as
    `ivcap.event.<key>` span attributes."""

    from ivcap_service import events

    span = DummySpan()
    tracer = DummyTracer(span)

    def _get_tracer(name: str):
        return tracer

    monkeypatch.setattr(events, "trace", None, raising=False)
    monkeypatch.setitem(
        __import__("sys").modules,
        "opentelemetry",
        type("otel", (), {"trace": type("trace", (), {"get_tracer": _get_tracer})})(),
    )

    r = events.EventReporter("job-123", None)
    with r.step("consume_compute") as ctxt:
        ctxt.finished(msg="done", run_time=1.23)

    assert span.attributes["ivcap.event.msg"] == "done"
    assert span.attributes["ivcap.event.run_time"] == 1.23


def test_non_primitive_kwargs_are_silently_skipped(monkeypatch: pytest.MonkeyPatch):
    """Values OTel can't represent as span attributes (e.g. dicts, mixed-type
    lists) must be silently skipped rather than raising."""

    from ivcap_service import events

    span = DummySpan()
    tracer = DummyTracer(span)

    def _get_tracer(name: str):
        return tracer

    monkeypatch.setattr(events, "trace", None, raising=False)
    monkeypatch.setitem(
        __import__("sys").modules,
        "opentelemetry",
        type("otel", (), {"trace": type("trace", (), {"get_tracer": _get_tracer})})(),
    )

    r = events.EventReporter("job-123", None)
    with r.step("my-step", extra={"nested": "dict"}, mixed=[1, "a"], ok=42) as _ctxt:
        pass

    assert "ivcap.event.extra" not in span.attributes
    assert "ivcap.event.mixed" not in span.attributes
    assert span.attributes["ivcap.event.ok"] == 42


def test_event_context_records_error(monkeypatch: pytest.MonkeyPatch):
    from ivcap_service import events

    span = DummySpan()
    tracer = DummyTracer(span)

    def _get_tracer(name: str):
        return tracer

    monkeypatch.setattr(events, "trace", None, raising=False)
    monkeypatch.setitem(
        __import__("sys").modules,
        "opentelemetry",
        type("otel", (), {"trace": type("trace", (), {"get_tracer": _get_tracer})})(),
    )

    r = events.EventReporter("job-123", None)
    with pytest.raises(ValueError):
        with r.step("explode") as _ctxt:
            raise ValueError("boom")

    # record_exception should have been called
    assert any("boom" in e for e in span.exceptions)
