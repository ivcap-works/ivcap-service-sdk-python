#
# Copyright (c) 2026 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
"""End-to-end test for the `--test-without-sidecar` CLI flag."""

import json

import pytest
from pydantic import BaseModel, Field

import ivcap_service.ivcap as ivcap_mod
from ivcap_service.ivcap import (
    is_sidecar_delivery_disabled,
    set_sidecar_delivery_disabled,
)
from ivcap_service.service import Service, ServiceContact, start_batch_service
from ivcap_service.types import JobContext


@pytest.fixture(autouse=True)
def _reset_sidecar_disabled_flag():
    set_sidecar_delivery_disabled(False)
    yield
    set_sidecar_delivery_disabled(False)


class Req(BaseModel):
    value: str = Field(description="input value")


class Res(BaseModel):
    value: str = Field(description="output value")


def _worker(req: Req, ctxt: JobContext) -> Res:
    ctxt.report.step_started("noop", message="starting")
    ctxt.report.step_finished("noop", message="done")
    return Res(value=req.value.upper())


def test_test_without_sidecar_flag_disables_delivery(
    tmp_path, monkeypatch: pytest.MonkeyPatch
):
    """Running with --test-file --test-without-sidecar must never attempt any
    HTTP call to the sidecar, even though IVCAP_BASE_URL is configured."""

    monkeypatch.setenv("IVCAP_BASE_URL", "http://ivcap.local")

    job_file = tmp_path / "job.json"
    job_file.write_text(
        json.dumps(
            {
                "id": "urn:ivcap:job:test-1",
                "in-content-type": "application/json",
                "in-content": {"value": "hello"},
            }
        )
    )

    called = False

    def _fake_post(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("httpx.post should not have been called")

    monkeypatch.setattr(ivcap_mod.httpx, "post", _fake_post)

    monkeypatch.setattr(
        "sys.argv",
        [
            "batch_service.py",
            "--test-file",
            str(job_file),
            "--test-without-sidecar",
        ],
    )

    service = Service(
        name="Test Service",
        contact=ServiceContact(name="Test", email="test@example.com"),
    )

    # `--test-file` mode runs the job once, prints the result and returns
    # normally (no sys.exit()).
    start_batch_service(service, _worker)

    assert called is False
    assert is_sidecar_delivery_disabled() is True
