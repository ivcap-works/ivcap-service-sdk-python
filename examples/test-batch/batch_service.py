import os
import sys
import math
from time import time
from typing import Optional
from pydantic import BaseModel, Field
from ivcap_service import getLogger, logging_init, JobContext
from ivcap_service.service import Service

this_dir = os.path.dirname(__file__)
src_dir = os.path.abspath(os.path.join(this_dir, "../../src"))
sys.path.insert(0, src_dir)

logging_init()
logger = getLogger("app")

service = Service(
    name="Batch service example",
    version=os.environ.get("VERSION", "???"),
    contact={
        "name": "Mary Doe",
        "email": "mary.doe@acme.au",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/license/MIT",
    },
)

class Request(BaseModel):
    jschema: str = Field("urn:sd:schema:batch-tester.request.1", alias="$schema")
    duration_seconds: Optional[int] = Field(10, description="seconds this job should run")
    target_cpu_percent: Optional[int] = Field(80, description="percentage load on CPU")
    throw_exception_at_end: Optional[bool] = Field(False, description="if True, throw an exception at the end of the job")
    exit_code_at_end: Optional[int] = Field(None, description="if set, exit with this code after the job is done")
    create_oom_error_at_end: Optional[bool]

class Result(BaseModel):
    jschema: str = Field("urn:sd:schema:batch-tester.1", alias="$schema")
    msg: str = Field(None, description="some message")
    run_time: float = Field(description="time in seconds this job took")

import time
import math

def consume_compute(req: Request, ctxt: JobContext) -> Result:
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

    if not 0 <= target_cpu_percent <= 100:
        raise ValueError("target_cpu_percent must be between 0 and 100")

    ctxt.report.step_started("consume_compute", f"Consuming CPU for {duration_seconds} seconds at {target_cpu_percent}%")
    start_time = time.time()
    end_time = start_time + duration_seconds
    logger.debug(f"Consuming CPU for {duration_seconds} seconds, targeting {target_cpu_percent}% per core...")

    # Constants to control the workload.  These may need adjustment.
    base_iterations = 10000  # A starting point for the loop iterations.
    load_factor = target_cpu_percent / 100.0  # Convert percentage to a fraction.

    loop_count = 0
    while time.time() < end_time:
        # Adjust the number of iterations to try to hit the target CPU.
        iterations = int(base_iterations * load_factor)

        # A simple loop with some math operations to consume CPU.
        for i in range(iterations):
            x = math.sqrt(i * 1.234)
            y = math.log(x + 1)
            z = math.pow(y, 2.345)
            w = math.sin(z)

        # A small sleep to prevent the loop from running *too* fast and
        # potentially starving other processes or causing issues.  The
        # optimal sleep time may vary by system.  If target_cpu_percent
        # is very high (e.g., > 90), this might need to be reduced or
        # eliminated.
        time.sleep(0.001)
        loop_count += 1

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
            data.append(' ' * 10_000_000)

    logger.info(msg)
    ctxt.report.step_finished("consume_compute", msg)
    return Result(msg="CPU consumption finished.", run_time=run_time)

# add_tool_api_route(app, "/", tester, opts=ToolOptions(tags=["Test Tool"], service_id="/"), context=ExecCtxt(msg="Boo!"))
# add_tool_api_route(app, "/async", async_tester, opts=ToolOptions(tags=["Test Tool"]))

if __name__ == "__main__":
    from ivcap_service import start_batch_service
    start_batch_service(service, consume_compute)
