#
# Copyright (c) 2025 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
"""
CPU load-test worker function (used for the 'consume_cpu' section of a
'test-batch' Request).
"""

import math
import sys
import time

from pydantic import BaseModel, Field

from ivcap_service import JobContext, getLogger

logger = getLogger("app")


class ConsumeComputeTester(BaseModel):
    duration_seconds: int | None = Field(10, description="seconds this job should run")
    target_cpu_percent: int | None = Field(80, description="percentage load on CPU")
    progress_interval_seconds: int | None = Field(
        5, description="how often (in seconds) a 'progress' event should be reported"
    )
    throw_exception_at_end: bool | None = Field(
        False, description="if True, throw an exception at the end of the job"
    )
    exit_code_at_end: int | None = Field(
        None, description="if set, exit with this code after the job is done"
    )
    create_oom_error_at_end: bool | None = Field(
        False, description="force an OOM error at end of run"
    )


class ConsumeComputeResult(BaseModel):
    msg: str = Field(..., description="a message describing the outcome of the CPU load test")
    run_time: float = Field(..., description="actual duration (in seconds) the CPU was consumed for")
    loops: int = Field(..., description="number of load-generating loop iterations performed")


def consume_compute(req: ConsumeComputeTester, ctxt: JobContext) -> ConsumeComputeResult:
    """
    Consumes a significant amount of CPU for a specified duration, useful for testing.

    This function attempts to consume a target percentage of CPU by performing
    mathematical operations in a loop.  It's single-threaded, so its
    effectiveness in consuming a specific percentage of *total* CPU will
    depend on the number of CPU cores available.  For example, on a
    quad-core machine, this function targeting 80% will consume roughly
    80% of one core's capacity, or 20% of the total CPU.

    Args:
        duration_seconds: The number of seconds to consume CPU.
        target_cpu_percent: The target CPU utilization as a percentage (0-100).
            Note that achieving a precise percentage is difficult due to
            Python's overhead and the nature of CPU scheduling.
    """
    duration_seconds = req.duration_seconds
    target_cpu_percent = req.target_cpu_percent
    progress_interval_seconds = req.progress_interval_seconds or 5

    if duration_seconds is None:
        raise ValueError("duration_seconds must be set")
    if target_cpu_percent is None or not 0 <= target_cpu_percent <= 100:
        raise ValueError("target_cpu_percent must be between 0 and 100")
    if progress_interval_seconds <= 0:
        raise ValueError("progress_interval_seconds must be positive")

    with ctxt.report.step(
        "consume_compute",
        f"Consuming CPU for {duration_seconds} seconds at {target_cpu_percent}%",
        duration_seconds=duration_seconds,
        target_cpu_percent=target_cpu_percent,
    ) as ectxt:
        start_time = time.time()
        end_time = start_time + duration_seconds
        logger.debug(
            f"Consuming CPU for {duration_seconds} seconds, targeting {target_cpu_percent}% per core..."
        )

        # Constants to control the workload.  These may need adjustment.
        base_iterations = 10000  # A starting point for the loop iterations.
        load_factor = target_cpu_percent / 100.0  # Convert percentage to a fraction.

        loop_count = 0
        last_progress_time = start_time
        while time.time() < end_time:
            # Adjust the number of iterations to try to hit the target CPU.
            iterations = int(base_iterations * load_factor)

            # A simple loop with some math operations to consume CPU.
            for i in range(iterations):
                x = math.sqrt(i * 1.234)
                y = math.log(x + 1)
                z = math.pow(y, 2.345)
                math.sin(z)

            # A small sleep to prevent the loop from running *too* fast and
            # potentially starving other processes or causing issues.  The
            # optimal sleep time may vary by system.  If target_cpu_percent
            # is very high (e.g., > 90), this might need to be reduced or
            # eliminated.
            time.sleep(0.001)
            loop_count += 1

            # Periodically report a 'progress' event so callers can track
            # how far along the job is without waiting for completion.
            now = time.time()
            if now - last_progress_time >= progress_interval_seconds:
                elapsed = now - start_time
                percent_complete = min(100.0, (elapsed / duration_seconds) * 100.0)
                ectxt.info(
                    event={
                        "message": f"progress: {percent_complete:.1f}% complete ({loop_count} loops)",
                        "elapsed_seconds": elapsed,
                        "duration_seconds": duration_seconds,
                        "percent_complete": percent_complete,
                        "loops": loop_count,
                    }
                )
                last_progress_time = now

        run_time = time.time() - start_time
        msg = f"CPU consumption finished after {run_time} sec (loops: {loop_count})"
        if req.throw_exception_at_end:
            msg += " - throwing an exception as requested."
            ctxt.report.step_finished("consume_compute", msg)
            raise RuntimeError(msg)

        if req.exit_code_at_end is not None:
            msg += f" - exiting with code {req.exit_code_at_end} as requested."
            ctxt.report.step_finished("consume_compute", msg)
            logger.info(msg)
            sys.exit(req.exit_code_at_end)

        if req.create_oom_error_at_end:
            # This script will eventually raise a MemoryError or be killed by the OS
            data = []
            while True:
                # Allocate 10MB chunks repeatedly
                data.append(" " * 10_000_000)

        ectxt.finished(actual_duration=run_time, loops=loop_count)

        return ConsumeComputeResult(msg=msg, run_time=run_time, loops=loop_count)
