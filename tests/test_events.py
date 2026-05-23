#
# Copyright (c) 2026 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
import json

import pytest

from ivcap_service.events import (
    BaseEvent,
    EventReporter,
    GenericErrorEvent,
    GenericEvent,
    StepErrorEvent,
    StepFinishEvent,
    StepInfoEvent,
    StepStartEvent,
    create_event_reporter,
    set_event_reporter_factory,
)


class TestEventSerialization:
    """Tests for event serialization."""

    def test_generic_event_model_dump(self):
        """Test GenericEvent serialization includes schema."""
        event = GenericEvent(name="test_event", options={"key": "value"})
        data = event.model_dump()
        assert data["$schema"] == "urn:ivcap:schema:service.event.generic.1"
        assert data["name"] == "test_event"
        assert data["options"] == {"key": "value"}

    def test_generic_event_model_dump_json(self):
        """Test GenericEvent JSON serialization."""
        event = GenericEvent(name="test_event")
        json_str = event.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["$schema"] == "urn:ivcap:schema:service.event.generic.1"
        assert parsed["name"] == "test_event"

    def test_step_start_event_schema(self):
        """Test StepStartEvent has correct schema."""
        event = StepStartEvent(name="step1", options={"step_number": 1})
        data = event.model_dump()
        assert data["$schema"] == "urn:ivcap:schema:service.event.step.start.1"
        assert data["name"] == "step1"

    def test_step_info_event_schema(self):
        """Test StepInfoEvent has correct schema."""
        event = StepInfoEvent(name="step1_info")
        data = event.model_dump()
        assert data["$schema"] == "urn:ivcap:schema:service.event.step.info.1"

    def test_step_finish_event_schema(self):
        """Test StepFinishEvent has correct schema."""
        event = StepFinishEvent(name="step1", options={"status": "completed"})
        data = event.model_dump()
        assert data["$schema"] == "urn:ivcap:schema:service.event.step.finish.1"

    def test_generic_error_event_schema(self):
        """Test GenericErrorEvent has correct schema."""
        event = GenericErrorEvent(
            error="Something went wrong",
            context="operation context",
            stacktrace=["line 1", "line 2"],
        )
        data = event.model_dump()
        assert data["$schema"] == "urn:ivcap:schema:service.event.error.1"
        assert data["error"] == "Something went wrong"
        assert data["context"] == "operation context"

    def test_step_error_event_schema(self):
        """Test StepErrorEvent has correct schema."""
        event = StepErrorEvent(error="Step failed", context="step execution")
        data = event.model_dump()
        assert data["$schema"] == "urn:ivcap:schema:service.event.step.error.1"

    def test_generic_event_optional_options(self):
        """Test GenericEvent with None options."""
        event = GenericEvent(name="test")
        data = event.model_dump()
        assert data["options"] is None

    def test_error_event_optional_context_and_stacktrace(self):
        """Test GenericErrorEvent with None context and stacktrace."""
        event = GenericErrorEvent(error="test error")
        data = event.model_dump()
        assert data["context"] is None
        assert data["stacktrace"] is None


class TestEventReporter:
    """Tests for EventReporter class."""

    def test_event_reporter_initialization(self):
        """Test EventReporter initialization."""
        reporter = EventReporter(job_id="job-123", job_authorization="auth-token")
        assert reporter.job_id == "job-123"
        assert reporter.job_authorization == "auth-token"

    def test_event_reporter_without_authorization(self):
        """Test EventReporter without authorization token."""
        reporter = EventReporter(job_id="job-123", job_authorization=None)
        assert reporter.job_id == "job-123"
        assert reporter.job_authorization is None

    def test_event_reporter_emit_accepts_event(self):
        """Test EventReporter.emit() accepts BaseEvent instances."""
        reporter = EventReporter(job_id="job-123", job_authorization=None)
        event = GenericEvent(name="test")
        # emit() should not raise any exceptions
        reporter.emit(event)

    def test_event_reporter_step_started(self):
        """Test EventReporter.step_started() creates StepStartEvent."""
        reporter = EventReporter(job_id="job-123", job_authorization=None)
        # This should not raise an exception
        reporter.step_started("my_step", message="Starting step")

    def test_event_reporter_step_finished(self):
        """Test EventReporter.step_finished() creates StepFinishEvent."""
        reporter = EventReporter(job_id="job-123", job_authorization=None)
        # This should not raise an exception
        reporter.step_finished("my_step", message="Step completed")

    def test_event_reporter_step_context_manager(self):
        """Test EventReporter.step() works as context manager."""
        reporter = EventReporter(job_id="job-123", job_authorization=None)
        with reporter.step("test_step", message="Running test") as ctx:
            assert ctx is not None
            assert ctx.name == "test_step"

    def test_event_reporter_step_context_manager_exit(self):
        """Test EventReporter.step() context manager cleanup."""
        reporter = EventReporter(job_id="job-123", job_authorization=None)
        with reporter.step("test_step"):
            pass
        # After exiting the context, finished should have been called
        # We can't directly verify this without mocking, but we ensure no exception


class TestEventFactory:
    """Tests for event factory functions."""

    def test_set_event_reporter_factory_valid(self):
        """Test setting a valid event reporter factory."""

        def custom_factory(job_id: str, job_authorization: str | None) -> EventReporter:
            return EventReporter(job_id, job_authorization)

        # Should not raise
        set_event_reporter_factory(custom_factory)

    def test_set_event_reporter_factory_none(self):
        """Test resetting factory to None."""
        # Should not raise
        set_event_reporter_factory(None)

    def test_set_event_reporter_factory_invalid(self):
        """Test setting non-callable as factory."""
        with pytest.raises(ValueError, match="Factory must be a callable"):
            set_event_reporter_factory("not a callable")  # type: ignore[arg-type]

    def test_create_event_reporter_default(self):
        """Test create_event_reporter with default factory."""
        reporter = create_event_reporter("job-123", "auth-token")
        assert isinstance(reporter, EventReporter)
        assert reporter.job_id == "job-123"
        assert reporter.job_authorization == "auth-token"

    def test_create_event_reporter_custom_factory(self):
        """Test create_event_reporter with custom factory."""

        class CustomReporter(EventReporter):
            pass

        def custom_factory(job_id: str, job_authorization: str | None) -> EventReporter:
            return CustomReporter(job_id, job_authorization)

        set_event_reporter_factory(custom_factory)
        reporter = create_event_reporter("job-456", None)
        assert isinstance(reporter, CustomReporter)
        # Reset to default
        set_event_reporter_factory(None)


class TestEventInheritance:
    """Tests for event class inheritance validation."""

    def test_custom_event_without_schema_raises(self):
        """Test that custom events without SCHEMA raise TypeError."""
        with pytest.raises(
            TypeError, match="must annotate SCHEMA as 'ClassVar\\[str\\]'"
        ):

            class BadEvent(BaseEvent):
                name: str

    def test_custom_event_with_valid_schema(self):
        """Test custom event with proper SCHEMA definition."""
        from typing import ClassVar

        class CustomEvent(BaseEvent):
            SCHEMA: ClassVar[str] = "urn:custom:schema"
            name: str

        event = CustomEvent(name="custom")
        data = event.model_dump()
        assert data["$schema"] == "urn:custom:schema"
