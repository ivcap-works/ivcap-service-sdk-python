#
# Copyright (c) 2025 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
import json
import os
import traceback
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Any, ClassVar

from pydantic import BaseModel, Field

from .logger import getLogger


class BaseEvent(BaseModel):
    SCHEMA: ClassVar[str]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if "SCHEMA" not in getattr(cls, "__annotations__", {}):
            raise TypeError(f"{cls.__name__} must annotate SCHEMA as 'ClassVar[str]'")
        if not hasattr(cls, "SCHEMA"):
            raise TypeError(f"{cls.__name__} must define a class constant 'SCHEMA'")

    def model_dump(self, *args, **kwargs):
        # Default to JSON-safe serialisation so that well-known
        # non-trivial types (HttpUrl, UUID, datetime, ...) are turned
        # into plain JSON-serialisable values, and fall back to `repr()`
        # for anything else Pydantic doesn't know how to serialise.
        # This prevents a caller passing e.g. an `HttpUrl` into step
        # options/kwargs from crashing event reporting (and thus
        # blocking the step body it wraps) with a
        # `PydanticSerializationError`/`TypeError`.
        kwargs.setdefault("mode", "json")
        kwargs.setdefault("fallback", repr)
        d = super().model_dump(*args, **kwargs)
        d["$schema"] = self.__class__.SCHEMA  # ty:ignore[unresolved-attribute]
        return d

    def model_dump_json(self, *args, **kwargs):
        # Only pass *args, **kwargs to model_dump, not to json.dumps
        return json.dumps(self.model_dump(*args, **kwargs))


class GenericEvent(BaseEvent):
    SCHEMA: ClassVar[str] = "urn:ivcap:schema:service.event.generic.1"
    name: str = Field(description="Name of event")
    options: dict[str, Any] | None = Field(
        default=None, description="Optional list of options"
    )


class GenericErrorEvent(BaseEvent):
    SCHEMA: ClassVar[str] = "urn:ivcap:schema:service.event.error.1"
    error: str = Field(description="Error description")
    context: str | None = Field(
        default=None, description="Optional description of context"
    )
    stacktrace: list[str] | None = Field(
        default=None, description="Optional stacktrace"
    )


class StepStartEvent(GenericEvent):
    SCHEMA: ClassVar[str] = "urn:ivcap:schema:service.event.step.start.1"


class StepInfoEvent(GenericEvent):
    SCHEMA: ClassVar[str] = "urn:ivcap:schema:service.event.step.info.1"


class StepErrorEvent(GenericErrorEvent):
    SCHEMA: ClassVar[str] = "urn:ivcap:schema:service.event.step.error.1"


class StepFinishEvent(GenericEvent):
    SCHEMA: ClassVar[str] = "urn:ivcap:schema:service.event.step.finish.1"


logger = getLogger("event")

event_reporter_factory = None

EventFactoryF = Callable[[str, str | None], "EventReporter"]


def set_event_reporter_factory(factory: EventFactoryF | None):
    """
    Set a factory function for creating specialised EventReporter instances.

    Args:
        factory (EventFactoryF | None): A factory function that takes a job ID and an optional job authorization token,
        and returns an instance of EventReporter. If None, the default EventReporter will be used.
    """
    global event_reporter_factory
    if factory is not None and not callable(factory):
        raise ValueError(
            "Factory must be a callable that returns an EventReporter instance."
        )
    event_reporter_factory = factory


def create_event_reporter(
    job_id: str, job_authorization: str | None = None
) -> "EventReporter":
    """
    Create an EventReporter instance for the given job ID.


    Args:
        job_id (str): The unique identifier for the job.
        job_authorization (Optional[str]): Optional authorization token for the job.

    Returns:
        EventReporter: An instance of EventReporter initialized with the job ID.
    """
    if event_reporter_factory is not None:
        return event_reporter_factory(job_id, job_authorization)
    return EventReporter(job_id, job_authorization)


def _otel_attribute_value(value: Any) -> Any:
    """Best-effort coercion of a value to something OTel span attributes
    accept: str, bool, int, float, or a homogeneous list/tuple of those.

    Returns None for values that can't be represented (e.g. dicts, None,
    arbitrary objects), so the caller can skip setting the attribute rather
    than raising.
    """
    if value is None:
        return None
    if isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, list | tuple):
        items = list(value)
        if not items:
            return items
        # OTel span attributes require homogeneously-typed sequences.
        first_type = type(items[0])
        if first_type in (bool, int, float, str) and all(
            type(v) is first_type for v in items
        ):
            return items
        return None
    return None


class EventContext:
    def __init__(
        self,
        event_name: str,
        reporter: "EventReporter",
        finishEventClass: type[GenericEvent] | None,
        errorEventClass: type[GenericErrorEvent] | None,
        span_attributes: dict[str, Any] | None = None,
    ):
        self._event_name = event_name
        self._reporter = reporter
        self._finishEventClass = finishEventClass
        self._errorEventClass = errorEventClass
        self._finished_sent = False

        # Best-effort OpenTelemetry child span for the event scope.
        # This should never break services that don't use OTEL.
        self._otel_span_cm = None
        self._otel_span = None
        try:
            from opentelemetry import trace

            tracer = trace.get_tracer("ivcap_service.events")
            self._otel_span_cm = tracer.start_as_current_span(
                f"ivcap.event:{event_name}"
            )
            self._otel_span = self._otel_span_cm.__enter__()
            try:
                self._otel_span.set_attribute("ivcap.job_id", reporter.job_id)
                self._otel_span.set_attribute("ivcap.event_name", event_name)
                service_id = os.getenv("IVCAP_SERVICE_ID")
                if service_id:
                    self._otel_span.set_attribute("ivcap.service_id", service_id)
                # Extra caller-supplied kwargs (e.g. from `report.step(..., foo=1)`)
                # are set as `ivcap.event.<key>` attributes, best-effort. Values
                # that OTel can't represent (dicts, None, mixed-type lists, ...)
                # are silently skipped rather than raising.
                for k, v in (span_attributes or {}).items():
                    coerced = _otel_attribute_value(v)
                    if coerced is not None:
                        self._otel_span.set_attribute(f"ivcap.event.{k}", coerced)
            except Exception:
                pass
        except Exception:
            pass

    @property
    def name(self):
        return self._event_name

    def finished(self, message=None, **kwargs):
        options = kwargs
        if message:
            options["message"] = message
        if self._finishEventClass:
            event = self._finishEventClass(name=self._event_name, options=options)
        else:
            event = GenericEvent(name=self._event_name, options=options)
        self._reporter.emit(event)
        self._finished_sent = True

        if self._otel_span is not None:
            try:
                for k, v in options.items():
                    coerced = _otel_attribute_value(v)
                    if coerced is not None:
                        self._otel_span.set_attribute(f"ivcap.event.{k}", coerced)
            except Exception:
                pass
            try:
                from opentelemetry.trace import Status, StatusCode

                self._otel_span.set_status(Status(StatusCode.OK))
            except Exception:
                pass

    def info(self, event: BaseEvent | dict):
        # We keep this ergonomic for callers: if they pass a raw dict,
        # wrap it into a generic event.
        if isinstance(event, BaseEvent):
            self._reporter.emit(event)
        else:
            self._reporter.emit(GenericEvent(name=self._event_name, options=event))

    def error(self, err: Exception, context: str | None = None):
        evc = (
            self._errorEventClass
            if self._errorEventClass is not None
            else GenericErrorEvent
        )
        stacktrace = traceback.format_tb(err.__traceback__)
        if not context:
            context = self._event_name
        event = evc(error=str(err), stacktrace=stacktrace, context=context)
        self._reporter.emit(event)

        if self._otel_span is not None:
            try:
                self._otel_span.record_exception(err)
            except Exception:
                pass
            try:
                from opentelemetry.trace import Status, StatusCode

                self._otel_span.set_status(
                    Status(StatusCode.ERROR, description=str(err))
                )
            except Exception:
                pass

    def close(self):
        """Close the underlying OTEL span if one was created."""

        if self._otel_span_cm is not None:
            try:
                self._otel_span_cm.__exit__(None, None, None)
            except Exception:
                pass
            finally:
                self._otel_span_cm = None
                self._otel_span = None

    def __del__(self):
        # Best-effort cleanup in case callers forget to exit the context.
        try:
            self.close()
        except Exception:
            pass


EventCtxtGenerator = Generator[EventContext, None, None]


class EventReporter:
    def __init__(self, job_id: str, job_authorization: str | None):
        self.job_id = job_id
        self.job_authorization = job_authorization

    def _send(self, event: BaseEvent):
        logger.debug(f"{self.job_id}: {event.model_dump_json(exclude_none=True)}")

    def emit(self, event: BaseEvent):
        self._send(event)

    def step_started(self, step_name: str, message=None, **kwargs):
        options = kwargs
        if message:
            options["message"] = message
        self.emit(StepStartEvent(name=step_name, options=options))

    def step_finished(self, step_name: str, message=None, **kwargs):
        options = kwargs
        if message:
            options["message"] = message
        self.emit(StepFinishEvent(name=step_name, options=options))

    def step(self, step_name, message=None, **kwargs):
        self.step_started(step_name, message, **kwargs)
        span_attributes = dict(kwargs)
        if message:
            span_attributes["message"] = message
        return self._event_scope(
            step_name,
            StepFinishEvent(name=step_name, options=None),
            StepErrorEvent,
            span_attributes=span_attributes,
        )

    @contextmanager
    def _event_scope(
        self,
        event_name: str,
        defaultFinishEvent: BaseEvent | None = None,
        errorEventClass: type[GenericErrorEvent] | None = None,
        span_attributes: dict[str, Any] | None = None,
    ) -> EventCtxtGenerator:
        fevc = (
            defaultFinishEvent.__class__
            if isinstance(defaultFinishEvent, GenericEvent)
            else None
        )
        ctxt = EventContext(event_name, self, fevc, errorEventClass, span_attributes)
        try:
            yield ctxt
        except Exception as e:
            ctxt.error(e, event_name)
            ctxt.close()
            raise e
        if not ctxt._finished_sent and defaultFinishEvent is not None:
            self.emit(defaultFinishEvent)
        ctxt.close()
