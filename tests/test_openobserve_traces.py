#
# Copyright (c) 2026 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
"""Regression tests for `_init_traces()`.

These guard against a real bug: `opentelemetry.trace.set_tracer_provider()`
can only ever succeed once per process (subsequent calls are silently
ignored, with only a warning logged). If an external auto-instrumentation
wrapper (e.g. `opentelemetry-instrument`) already installed a TracerProvider
before our SDK code runs, naively calling `set_tracer_provider()` again would
silently drop our OpenObserve exporter - spans would keep being created, but
never exported. `_init_traces()` must instead attach its span processor to
the already-active provider via `add_span_processor()`.
"""

import logging

import pytest


@pytest.fixture(autouse=True)
def _reset_tracer_provider():
    """Reset the global TracerProvider around each test.

    `opentelemetry.trace._TRACER_PROVIDER` is a module-level singleton
    guarded by a `Once()`; we reset it directly so each test starts from a
    clean slate (mirrors patterns used by opentelemetry's own test suite).
    """
    from opentelemetry import trace
    from opentelemetry.util._once import Once

    yield

    trace._TRACER_PROVIDER = None  # type: ignore[attr-defined]
    trace._TRACER_PROVIDER_SET_ONCE = Once()  # type: ignore[attr-defined]


def test_init_traces_attaches_to_existing_tracer_provider(monkeypatch):
    """When a TracerProvider is already installed (e.g. by an external
    auto-instrumentation agent), _init_traces() must attach its exporter to
    it instead of silently failing to install a new one.
    """
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider

    from ivcap_service.openobserve import (
        _init_traces,
        load_openobserve_config_from_env,
    )

    # Simulate an external `opentelemetry-instrument` wrapper that already
    # claimed the global TracerProvider before our code runs.
    external_tp = TracerProvider(
        resource=Resource.create({"service.name": "b-batch-servic-e08ec67832ca"})
    )
    trace.set_tracer_provider(external_tp)
    assert trace.get_tracer_provider() is external_tp

    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318")
    monkeypatch.setenv("OPENOBSERVE_ENABLED", "true")

    cfg = load_openobserve_config_from_env(service_name="svc")
    assert cfg is not None

    _init_traces(cfg, Resource.create({}), logging.getLogger("test"))

    # The global provider must still be the external one (we never try to
    # replace it - that would silently fail anyway).
    active = trace.get_tracer_provider()
    assert active is external_tp

    # Our exporter must have been attached to it.
    assert getattr(active, "_ivcap_openobserve", False) is True
    span_processors = active._active_span_processor._span_processors  # type: ignore[attr-defined]
    assert len(span_processors) == 1


def test_init_traces_installs_new_provider_when_none_active(monkeypatch):
    """When no TracerProvider is active yet, _init_traces() should install
    its own, as before."""
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider

    from ivcap_service.openobserve import (
        _init_traces,
        load_openobserve_config_from_env,
    )

    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318")
    monkeypatch.setenv("OPENOBSERVE_ENABLED", "true")

    cfg = load_openobserve_config_from_env(service_name="svc")
    assert cfg is not None

    _init_traces(cfg, Resource.create({"service.name": "svc"}), logging.getLogger("test"))

    active = trace.get_tracer_provider()
    assert isinstance(active, TracerProvider)
    assert getattr(active, "_ivcap_openobserve", False) is True


def test_init_traces_is_idempotent(monkeypatch):
    """Calling _init_traces() twice must not attach the exporter twice."""
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource

    from ivcap_service.openobserve import (
        _init_traces,
        load_openobserve_config_from_env,
    )

    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318")
    monkeypatch.setenv("OPENOBSERVE_ENABLED", "true")

    cfg = load_openobserve_config_from_env(service_name="svc")
    assert cfg is not None

    resource = Resource.create({"service.name": "svc"})
    _init_traces(cfg, resource, logging.getLogger("test"))
    _init_traces(cfg, resource, logging.getLogger("test"))

    active = trace.get_tracer_provider()
    span_processors = active._active_span_processor._span_processors  # type: ignore[attr-defined]
    assert len(span_processors) == 1
