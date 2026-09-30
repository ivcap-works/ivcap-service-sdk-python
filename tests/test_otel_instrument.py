#
# Copyright (c) 2026 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
"""Tests for the tri-state `otel_instrument()` auto-enable behaviour.

`with_telemetry` has three meaningful states:
- `None` (default) - auto-enable instrumentation whenever
  `OTEL_EXPORTER_OTLP_ENDPOINT` is configured.
- `True` (`--with-telemetry`) - force-enable, warning if no endpoint is set.
- `False` (`--without-telemetry`) - force-disable, even if an endpoint is set.
"""

import logging

import pytest


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)


def test_auto_enables_when_endpoint_configured_and_no_flag(monkeypatch):
    """`with_telemetry=None` + endpoint set => instrumentation attempted."""
    from ivcap_service.context import otel_instrument

    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318")
    logger = logging.getLogger("test.otel_instrument")

    called = []
    otel_instrument(None, lambda endpoint: called.append(endpoint), logger)

    assert called == ["http://collector:4318"]


def test_no_op_when_no_endpoint_and_no_flag(monkeypatch, caplog):
    """`with_telemetry=None` + no endpoint => silent no-op (no warning)."""
    from ivcap_service.context import otel_instrument

    logger = logging.getLogger("test.otel_instrument")

    called = []
    with caplog.at_level(logging.WARNING, logger="test.otel_instrument"):
        otel_instrument(None, lambda endpoint: called.append(endpoint), logger)

    assert called == []
    assert not any("with-telemetry" in r.message for r in caplog.records)


def test_force_enable_warns_when_no_endpoint(monkeypatch, caplog):
    """`with_telemetry=True` + no endpoint => warns, still a no-op."""
    from ivcap_service.context import otel_instrument

    logger = logging.getLogger("test.otel_instrument")

    called = []
    with caplog.at_level(logging.WARNING, logger="test.otel_instrument"):
        otel_instrument(True, lambda endpoint: called.append(endpoint), logger)

    assert called == []
    assert any("with-telemetry" in r.message for r in caplog.records)


def test_force_enable_with_endpoint(monkeypatch):
    """`with_telemetry=True` + endpoint set => instrumentation attempted."""
    from ivcap_service.context import otel_instrument

    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318")
    logger = logging.getLogger("test.otel_instrument")

    called = []
    otel_instrument(True, lambda endpoint: called.append(endpoint), logger)

    assert called == ["http://collector:4318"]


def test_force_disable_even_with_endpoint(monkeypatch):
    """`with_telemetry=False` + endpoint set => still disabled."""
    from ivcap_service.context import otel_instrument

    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318")
    logger = logging.getLogger("test.otel_instrument")

    called = []
    otel_instrument(False, lambda endpoint: called.append(endpoint), logger)

    assert called == []


def test_force_disable_without_endpoint(monkeypatch):
    """`with_telemetry=False` + no endpoint => no-op, no warning either."""
    from ivcap_service.context import otel_instrument

    logger = logging.getLogger("test.otel_instrument")

    called = []
    otel_instrument(False, lambda endpoint: called.append(endpoint), logger)

    assert called == []
