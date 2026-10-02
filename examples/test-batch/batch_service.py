import math
import os
import sys
import time
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field, HttpUrl

from ivcap_service import (
    JobContext,
    Service,
    ServiceContact,
    ServiceLicense,
    getLogger,
    logging_init,
    with_schema,
)

this_dir = os.path.dirname(__file__)
src_dir = os.path.abspath(os.path.join(this_dir, "../../src"))
sys.path.insert(0, src_dir)

logging_init()
logger = getLogger("app")

service = Service(
    name="Batch service example",
    version=os.environ.get("VERSION", "???"),
    contact=ServiceContact(
        name="Mary Doe",
        email="mary.doe@acme.au",
    ),
    license=ServiceLicense(
        name="MIT",
        url="https://opensource.org/license/MIT",
    ),
)


class CallTester(BaseModel):
    method: str = Field(
        ...,
        description="The HTTP method to use (GET, POST, PUT, DELETE, etc.).",
        pattern="^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)$",  # Only allow valid methods
    )
    url: HttpUrl = Field(..., description="The full URL of the API endpoint.")
    params: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional dictionary of query parameters to be appended to the URL.",
    )
    data: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional JSON payload to be sent in the request body (for POST/PUT).",
    )
    headers: Optional[Dict[str, str]] = Field(
        None, description="Optional dictionary of headers to include in the request."
    )
    timeout: int = Field(
        5,
        description="The timeout duration for the request in seconds.",
        ge=1,  # Minimum value of 1 second to prevent infinite waiting
    )


class ChatMessage(BaseModel):
    content: str = Field(..., description="The content of this message.")
    role: str = Field(..., description="The role of the messages author.")
    name: Optional[str] = Field(
        None, description="An optional name for the participant."
    )


class LlmTester(BaseModel):
    messages: List[ChatMessage] = Field(
        ..., description="A list of messages to be passed to the LLM."
    )
    model: Optional[str] = Field(
        "sciansa-default", description="The LLM model to use [gpt-3.5-turbo]."
    )


@with_schema("urn:sd:schema:batch-tester.request.1")
class Request(BaseModel):
    duration_seconds: int | None = Field(10, description="seconds this job should run")
    target_cpu_percent: int | None = Field(80, description="percentage load on CPU")
    throw_exception_at_end: bool | None = Field(
        False, description="if True, throw an exception at the end of the job"
    )
    exit_code_at_end: int | None = Field(
        None, description="if set, exit with this code after the job is done"
    )
    create_oom_error_at_end: bool | None = Field(
        False, description="force an OOM error at end of run"
    )
    echo: Optional[str] = Field(None, description="a string to echo in result")
    call: Optional[CallTester] = Field(None, description="Optionally call a service")
    llm: Optional[LlmTester] = Field(
        None, description="Optionally callan LLM's completion service"
    )


@with_schema("urn:sd:schema:batch-tester.1")
class Result(BaseModel):
    msg: str | None = Field(None, description="some message")
    run_time: float = Field(description="time in seconds this job took")
    echo: Optional[str] = Field(None, description="echos string from request")
    call_result: Optional[Dict] = Field(
        None, description="result of executing the 'call'"
    )
    llm_result: Optional[Dict] = Field(
        None, description="result of executing the 'llm'"
    )


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

        result = Result(msg=msg, run_time=run_time)

        if req.echo is not None:
            result.echo = req.echo

        if req.call is not None:
            result.call_result = make_request(req.call, ctxt)

        if req.llm is not None:
            result.llm_result = completion(req.llm)

        return result


def make_request(req: CallTester, ctxt: JobContext) -> Any:
    """
    Makes a generic HTTP request.

    :param req: CallTester object containing request details.
    :return: JSON response or error message.
    """
    with ctxt.report.step(
        "make_call",
        f"Making HTTP call to {req.url}",
        url=req.url,
        method=req.method,
        params=req.params,
        data=req.data,
        headers=req.headers,
        timeout=req.timeout,
    ):
        try:
            url = str(req.url)
            response = httpx.request(
                method=req.method.upper(),
                url=url,
                params=req.params,
                json=req.data,
                headers=req.headers,
                timeout=req.timeout,
            )
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx, 5xx)
            return response.json()

        except httpx.HTTPError as e:
            return {"error": str(e)}


def completion(req: LlmTester):
    import openai

    try:
        client = create_openai_client(openai.OpenAI)
        response = client.chat.completions.create(
            model=req.model, messages=[m.model_dump() for m in req.messages]
        )
        return format_llm_response(response)
    except Exception as ex:
        logger.warning(f"llm execution failed - {ex}")
        raise ex


def format_llm_response(response):
    messages = [c.message.model_dump() for c in response.choices]
    usage = response.usage.model_dump()
    return {"messages": messages, "usage": usage}


def create_openai_client(f):
    base_url = os.getenv("LITELLM_PROXY")
    if base_url is None:
        return f()
    else:
        return f(base_url=f"{base_url}/v1", api_key="not-needed")


if __name__ == "__main__":
    from ivcap_service import start_batch_service

    start_batch_service(service, consume_compute)
