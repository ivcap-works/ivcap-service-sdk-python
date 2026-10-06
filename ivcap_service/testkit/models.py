#
# Copyright (c) 2025 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
"""
Top-level Request/Result Pydantic models for the 'test-batch' example
service.

Each sub-test's own request/result models (e.g. 'CallTester',
'LlmTester'/'LlmResult', 'ArtifactTester'/'ArtifactResult',
'ConsumeComputeTester'/'ConsumeComputeResult', 'WordleTester'/'WordleResult')
are declared alongside their implementation in the corresponding module, and
simply imported here for composition into the top-level 'Request'/'Result'.

The 'call' sub-test is the one exception: its result has no fixed shape (it
is whatever JSON the called endpoint returns), so 'call_result' remains a
plain 'dict'.
"""

from pydantic import BaseModel, Field

from ivcap_service import with_schema

from .artifact import ArtifactResult, ArtifactTester
from .call import CallTester
from .consume_compute import ConsumeComputeResult, ConsumeComputeTester
from .events import EventResult, EventTester
from .llm import LlmResult, LlmTester
from .wordle import WordleResult, WordleTester


@with_schema("urn:sd:schema:batch-tester.request.1")
class Request(BaseModel):
    echo: str | None = Field(None, description="a string to echo in result")
    consume_cpu: ConsumeComputeTester | None = Field(
        None,
        description=(
            "Optionally consume a target percentage of CPU for a given duration "
            "- useful for load testing"
        ),
    )
    call: CallTester | None = Field(None, description="Optionally call a service")
    llm: LlmTester | None = Field(
        None, description="Optionally callan LLM's completion service"
    )
    artifact: ArtifactTester | None = Field(
        None,
        description="Optionally download an artifact (and optionally re-upload it)",
    )
    wordle: WordleTester | None = Field(
        None,
        description="Optionally play a game of Wordle with a built-in AI solver",
    )
    events: EventTester | None = Field(
        None,
        description="Optionally emit a number of progress events",
    )


@with_schema("urn:sd:schema:batch-tester.1")
class Result(BaseModel):
    msg: str | None = Field(None, description="some message")
    run_time: float = Field(description="time in seconds this job took")
    echo: str | None = Field(None, description="echos string from request")
    consume_result: ConsumeComputeResult | None = Field(
        None, description="result of executing the 'consume_cpu' CPU load test"
    )
    call_result: dict | None = Field(
        None, description="result of executing the 'call'"
    )
    llm_result: LlmResult | None = Field(
        None, description="result of executing the 'llm'"
    )
    artifact_result: ArtifactResult | None = Field(
        None, description="result of executing the 'artifact' download/upload"
    )
    wordle_result: WordleResult | None = Field(
        None, description="result of executing the 'wordle' game"
    )
    event_result: EventResult | None = Field(
        None, description="result of executing the 'events' test"
    )

