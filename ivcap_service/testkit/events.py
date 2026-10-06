#
# Copyright (c) 2025 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
"""
Event-emission worker function (used for the 'events' section of a
'test-batch' Request).

Emits a configurable number of progress 'step' events (optionally sleeping
between each one), followed by a single 'finished' event - useful for
exercising/testing event-streaming and progress-reporting plumbing without
depending on any other sub-test.
"""

from time import sleep

from pydantic import BaseModel, Field

from ivcap_service import GenericEvent, JobContext


class EventTester(BaseModel):
    count: int = Field(5, description="Number of events to send")
    sleep: int = Field(
        1, description="the number of seconds to sleep until next event"
    )


class EventResult(BaseModel):
    count: int = Field(..., description="number of events actually sent")


def send_events(req: EventTester, ctxt: JobContext) -> EventResult:
    """
    Emits 'req.count' progress 'step' events (sleeping 'req.sleep' seconds
    between each one), followed by a single 'finished' generic event.

    :param req: EventTester object containing the number of events to send
        and the delay (in seconds) between them.
    :return: an EventResult reporting how many events were sent.
    """
    for i in range(req.count):
        with ctxt.report.step("work", message=f"step#{i}"):
            sleep(req.sleep)
    ctxt.report.emit(GenericEvent(name="finished"))
    return EventResult(count=req.count)
