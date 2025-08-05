#
# Copyright (c) 2025 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
from contextlib import contextmanager
import time
import traceback
from typing import Any, Callable, Generator, List, Optional
from ag_ui.core.events import (
    TextMessageStartEvent, TextMessageContentEvent, TextMessageEndEvent,
    ToolCallStartEvent, ToolCallArgsEvent, ToolCallEndEvent,
    StateSnapshotEvent, StateDeltaEvent, MessagesSnapshotEvent,
    RawEvent, CustomEvent, RunStartedEvent, RunFinishedEvent,
    RunErrorEvent, StepStartedEvent, StepFinishedEvent, EventType, BaseEvent
)
from ag_ui.core.types import Message, State


from .logger import getLogger

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
    def __init__(self, event_name:str):
        self._event_name = event_name
        self._exit_msg = None
        self._exit_timestamp = None

    def finished(self, msg: Optional[Any] = None, timestamp: Optional[int] = None):
        self._exit_msg = msg
        self._exit_timestamp = timestamp

    def _finished(self, finish_fn):
        finish_fn(self._event_name, self._exit_msg, self._exit_timestamp)

EventCtxtGenerator = Generator[EventContext, None, None]

class EventReporter:
    def __init__(self, job_id: str, job_authorization: str):
        self.job_id = job_id
        self.job_authorization = job_authorization

    def _send(self, event: BaseEvent):
        logger.debug(f"{self.job_id}: {event.model_dump_json(exclude_none=True)}")

    def _emit(self, cls, event_type, **kwargs):
        try:
            event = cls(type=event_type, **kwargs)
            if event.timestamp is None:
                    event.timestamp = int(time.time() * 1000)
            self._send(event)
        except Exception as e:
            logger.error(f"Failed to emit event {event_type}: {e}")

    def text_message_start(self, message_id: str, role: str, raw_event: Optional[Any] = None, timestamp: Optional[int] = None):
        self._emit(TextMessageStartEvent, EventType.TEXT_MESSAGE_START, message_id=message_id, role=role, raw_event=raw_event, timestamp=timestamp)

    def text_message_content(self, message_id: str, delta: str, raw_event: Optional[Any] = None, timestamp: Optional[int] = None):
        self._emit(TextMessageContentEvent, EventType.TEXT_MESSAGE_CONTENT, message_id=message_id, delta=delta, raw_event=raw_event, timestamp=timestamp)

    def text_message_end(self, message_id: str, raw_event: Optional[Any] = None, timestamp: Optional[int] = None):
        self._emit(TextMessageEndEvent, EventType.TEXT_MESSAGE_END, message_id=message_id, raw_event=raw_event, timestamp=timestamp)

    def tool_call_start(self, tool_call_id: str, tool_call_name: str, parent_message_id: Optional[str] = None, raw_event: Optional[Any] = None, timestamp: Optional[int] = None):
        self._emit(ToolCallStartEvent, EventType.TOOL_CALL_START, tool_call_id=tool_call_id, tool_call_name=tool_call_name, parent_message_id=parent_message_id, raw_event=raw_event, timestamp=timestamp)

    def tool_call_args(self, tool_call_id: str, delta: str, raw_event: Optional[Any] = None, timestamp: Optional[int] = None):
        self._emit(ToolCallArgsEvent, EventType.TOOL_CALL_ARGS, tool_call_id=tool_call_id, delta=delta, raw_event=raw_event, timestamp=timestamp)

    def tool_call_end(self, tool_call_id: str, raw_event: Optional[Any] = None, timestamp: Optional[int] = None):
        self._emit(ToolCallEndEvent, EventType.TOOL_CALL_END, tool_call_id=tool_call_id, raw_event=raw_event, timestamp=timestamp)

    def state_snapshot(self, snapshot: State, raw_event: Optional[Any] = None, timestamp: Optional[int] = None):
        self._emit(StateSnapshotEvent, EventType.STATE_SNAPSHOT, snapshot=snapshot, raw_event=raw_event, timestamp=timestamp)

    def state_delta(self, delta: List[Any], raw_event: Optional[Any] = None, timestamp: Optional[int] = None):
        self._emit(StateDeltaEvent, EventType.STATE_DELTA, delta=delta, raw_event=raw_event, timestamp=timestamp)

    def messages_snapshot(self, messages: List[Message], raw_event: Optional[Any] = None, timestamp: Optional[int] = None):
        self._emit(MessagesSnapshotEvent, EventType.MESSAGES_SNAPSHOT, messages=messages, raw_event=raw_event, timestamp=timestamp)

    def raw(self, event: Any, source: Optional[str] = None, raw_event: Optional[Any] = None, timestamp: Optional[int] = None):
        self._emit(RawEvent, EventType.RAW, event=event, source=source, raw_event=raw_event, timestamp=timestamp)

    def custom(self, name: str, value: Any, raw_event: Optional[Any] = None, timestamp: Optional[int] = None):
        self._emit(CustomEvent, EventType.CUSTOM, name=name, value=value, raw_event=raw_event, timestamp=timestamp)

    def run_started(self, thread_id: str, run_id: str, raw_event: Optional[Any] = None, timestamp: Optional[int] = None):
        self._emit(RunStartedEvent, EventType.RUN_STARTED, thread_id=thread_id, run_id=run_id, raw_event=raw_event, timestamp=timestamp)

    def run_finished(self, thread_id: str, run_id: str, raw_event: Optional[Any] = None, timestamp: Optional[int] = None):
        self._emit(RunFinishedEvent, EventType.RUN_FINISHED, thread_id=thread_id, run_id=run_id, raw_event=raw_event, timestamp=timestamp)

    def run_error(self, message: str, code: Optional[str] = None, raw_event: Optional[Any] = None, timestamp: Optional[int] = None):
        self._emit(RunErrorEvent, EventType.RUN_ERROR, message=message, code=code, raw_event=raw_event, timestamp=timestamp)

    def step_started(self, step_name: str, raw_event: Optional[Any] = None, timestamp: Optional[int] = None):
        self._emit(StepStartedEvent, EventType.STEP_STARTED, step_name=step_name, raw_event=raw_event, timestamp=timestamp)

    def step_finished(self, step_name: str, raw_event: Optional[Any] = None, timestamp: Optional[int] = None):
        self._emit(StepFinishedEvent, EventType.STEP_FINISHED, step_name=step_name, raw_event=raw_event, timestamp=timestamp)

    def step(self, step_name, raw_event=None, timestamp=None):
        return self._event_scope(step_name, self.step_started, self.step_finished, raw_event, timestamp)

    @contextmanager
    def _event_scope(
        self,
        event_name: str,
        start_fn: Callable[[str, Optional[Any], Optional[int]], None],
        finish_fn: Callable[[str, Optional[Any], Optional[int]], None],
        raw_event: Optional[Any] = None,
        timestamp: Optional[int] = None
    ) -> EventCtxtGenerator:
        ctxt = EventContext(event_name)
        start_fn(event_name, raw_event, timestamp)
        try:
            yield ctxt
        except Exception as e:
            import traceback
            trace = traceback.format_exc()
            self.run_error(f"exception in event '{event_name}' - {str(e)}", trace)
            raise e
        ctxt._finished(finish_fn)