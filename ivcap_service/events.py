#
# Copyright (c) 2025 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
from contextlib import contextmanager
import traceback
from typing import Any, Callable, ClassVar, Generator, Optional, Type
from pydantic import BaseModel, Field
import json

from .logger import getLogger

class BaseEvent(BaseModel):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if 'SCHEMA' not in getattr(cls, '__annotations__', {}):
            raise TypeError(f"{cls.__name__} must annotate SCHEMA as 'ClassVar[str]'")
        if not hasattr(cls, 'SCHEMA'):
            raise TypeError(f"{cls.__name__} must define a class constant 'SCHEMA'")

    def model_dump(self, *args, **kwargs):
        d = super().model_dump(*args, **kwargs)
        d["$schema"] = self.__class__.SCHEMA
        return d

    def model_dump_json(self, *args, **kwargs):
        # Only pass *args, **kwargs to model_dump, not to json.dumps
        return json.dumps(self.model_dump(*args, **kwargs))

class GenericEvent(BaseEvent):
    SCHEMA: ClassVar[str] = "urn:ivcap:schema:service.event.generic.1"
    name: str = Field(description="Name of event")
    options: Optional[dict[str, Any]] = Field(None, description="Optional list of options")

class GenericErrorEvent(BaseEvent):
    SCHEMA: ClassVar[str]= "urn:ivcap:schema:service.event.error.1"
    error: str = Field(description="Error description")
    context: Optional[str] = Field(None, description="Optional description of context")
    stacktrace:  Optional[list[str]] = Field(None, description="Optional stacktrace")


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

EventFactoryF = Callable[[str, Optional[str]], 'EventReporter']
def set_event_reporter_factory(factory: EventFactoryF):
    """
    Set afactory function for creating specialised EventReporter instances.

    Args:
        factory (EventFactoryF): A factory function that takes a job ID and an optional job authorization token,
        and returns an instance of EventReporter. If None, the default EventReporter will be used.
    """
    global event_reporter_factory
    if factory is not None and not callable(factory):
        raise ValueError("Factory must be a callable that returns an EventReporter instance.")
    event_reporter_factory = factory

def create_event_reporter(job_id: str, job_authorization: Optional[str] = None) -> 'EventReporter':
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

class EventContext:
    def __init__(self,
                 event_name:str,
                 reporter:'EventReporter',
                 finishEventClass: Optional[Type[BaseEvent]],
                 errorEventClass: Optional[Type[GenericErrorEvent]]
        ):
        self._event_name = event_name
        self._reporter = reporter
        self._finishEventClass = finishEventClass
        self._errorEventClass = errorEventClass
        self._finished_sent = False

    @property
    def name(self):
        return self._event_name

    def finished(self, message=None, **kwargs):
        options=kwargs
        if message:
            options["message"] = message
        if self._finishEventClass:
            event = self._finishEventClass(name=self._event_name, options=options)
        else:
            event = GenericEvent(name=self._event_name, options=options)
        self._reporter.emit(event)
        self._finished_sent = True

    def info(self, event: BaseEvent | dict):
        self._reporter.emit(event)

    def error(self, err: Exception, context: Optional[str]=None):
        evc = self._errorEventClass if self._errorEventClass is not None else GenericErrorEvent
        stacktrace = traceback.format_tb(err.__traceback__)
        if not context:
            context = self._event_name
        event = evc(error=str(err), stacktrace=stacktrace, context=context)
        self._reporter.emit(event)

EventCtxtGenerator = Generator[EventContext, None, None]

class EventReporter:
    def __init__(self, job_id: str, job_authorization: str):
        self.job_id = job_id
        self.job_authorization = job_authorization

    def _send(self, event: BaseEvent):
        logger.debug(f"{self.job_id}: {event.model_dump_json(exclude_none=True)}")

    def emit(self, event: BaseEvent):
        self._send(event)

    def step_started(self, step_name: str, message=None, **kwargs):
        options=kwargs
        if message:
            options["message"] = message
        self.emit(StepStartEvent(name=step_name, options=options))

    def step_finished(self, step_name: str, message=None, **kwargs):
        options=kwargs
        if message:
            options["message"] = message
        self.emit(StepFinishEvent(name=step_name, options=options))

    def step(self, step_name, message=None, **kwargs):
        self.step_started(step_name, message, **kwargs)
        return self._event_scope(step_name, StepFinishEvent(name=step_name), StepErrorEvent)

    @contextmanager
    def _event_scope(
        self,
        event_name: str,
        defaultFinishEvent: Optional[BaseEvent] = None,
        errorEventClass: Optional[Type[GenericErrorEvent]] = None,
    ) -> EventCtxtGenerator:
        fevc = defaultFinishEvent.__class__ if defaultFinishEvent else None
        ctxt = EventContext(event_name, self, fevc, errorEventClass)
        try:
            yield ctxt
        except Exception as e:
            ctxt.error(e, event_name)
            raise e
        if not ctxt._finished_sent:
            self.emit(defaultFinishEvent)
