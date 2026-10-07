#
# Copyright (c) 2025 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
"""
Reusable test/load-test worker functions ('testkit') shipped as part of the
'ivcap_service' package.

This package contains the Request/Result models and all worker functions
originally developed for the 'examples/test-batch' example service. It has
been promoted into the installable package (as 'ivcap_service.testkit') so
that the same test methods can be imported and reused by other projects
(e.g. the 'ivcap-lambda' SDK) for their own tests, without having to
duplicate this code or depend on the 'examples/' tree.

Each sub-test lives in its own module, declaring both its request model
and its worker function together:
    - 'models' - top-level Request/Result Pydantic models
    - 'consume_compute' - CPU load test ('req.consume_cpu')
    - 'call' - generic HTTP call ('req.call')
    - 'llm' - LLM completion call ('req.llm')
    - 'artifact' - artifact download/upload ('req.artifact')
    - 'wordle' - Wordle game simulation ('req.wordle')

This '__init__.py' wires them back together into the single
'process_job(req, ctxt)' entry point, and re-exports the public symbols so
that 'from ivcap_service.testkit import ...' works.
"""

import time

from ivcap_service import DEFAULT_LLM_MODEL, JobContext, getLogger

from .artifact import (
    DEFAULT_ARTIFACT_CHUNK_SIZE_BYTES,
    ArtifactResult,
    ArtifactTester,
    handle_artifact,
)
from .call import CallTester, make_request
from .consume_compute import ConsumeComputeResult, ConsumeComputeTester, consume_compute
from .events import EventResult, EventTester, send_events
from .llm import ChatMessage, LlmResult, LlmTester, completion
from .models import Request, Result
from .wordle import WordleResult, WordleTester, handle_wordle

__all__ = [
    "DEFAULT_ARTIFACT_CHUNK_SIZE_BYTES",
    "DEFAULT_LLM_MODEL",
    "ArtifactResult",
    "ArtifactTester",
    "CallTester",
    "ChatMessage",
    "ConsumeComputeResult",
    "ConsumeComputeTester",
    "EventResult",
    "EventTester",
    "LlmResult",
    "LlmTester",
    "Request",
    "Result",
    "WordleResult",
    "WordleTester",
    "process_job",
    "consume_compute",
    "make_request",
    "completion",
    "handle_artifact",
    "handle_wordle",
    "send_events",
]

logger = getLogger("app")


def process_job(req: Request, ctxt: JobContext) -> Result:
    """
    General entry point for the 'test-batch' example service.

    None of the sub-tests are mandatory - each one is only run if the
    corresponding optional section is present in the request:

    - 'consume_cpu': runs 'consume_compute()' to burn CPU for a given
      duration/target load - useful for load testing.
    - 'call': runs 'make_request()' to make a generic HTTP call.
    - 'llm': runs 'completion()' to exercise an LLM's completion endpoint.
    - 'artifact': runs 'handle_artifact()' to download (and optionally
      re-upload) an artifact.
    - 'wordle': runs 'handle_wordle()' to simulate a game of Wordle played
      by a built-in AI solver.
    - 'events': runs 'send_events()' to emit a configurable number of
      progress events.

    If none of the optional sections are provided, the job simply completes
    (echoing back 'req.echo' if set).
    """
    start_time = time.time()
    result = Result(run_time=0.0)

    if req.echo is not None:
        result.echo = req.echo

    if req.consume_cpu is not None:
        result.consume_result = consume_compute(req.consume_cpu, ctxt)

    if req.call is not None:
        result.call_result = make_request(req.call, ctxt)

    if req.llm is not None:
        result.llm_result = completion(req.llm, ctxt)

    if req.artifact is not None:
        result.artifact_result = handle_artifact(req.artifact, ctxt)

    if req.wordle is not None:
        result.wordle_result = handle_wordle(req.wordle, ctxt)

    if req.events is not None:
        result.event_result = send_events(req.events, ctxt)

    result.run_time = time.time() - start_time
    result.msg = f"job finished after {result.run_time} sec"
    return result
