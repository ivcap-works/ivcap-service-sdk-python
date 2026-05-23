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
