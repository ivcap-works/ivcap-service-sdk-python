import io
import math
import os
import sys
import time
from typing import Any, Dict, Iterator, List, Optional

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


DEFAULT_ARTIFACT_CHUNK_SIZE_BYTES = 1_048_576  # 1MB


class LlmTester(BaseModel):
    messages: List[ChatMessage] = Field(
        ..., description="A list of messages to be passed to the LLM."
    )
    model: Optional[str] = Field(
        "sciansa-default", description="The LLM model to use [gpt-3.5-turbo]."
    )


class ArtifactTester(BaseModel):
    artifact_urn: str = Field(
        ..., description="URN of the artifact to download, e.g. 'urn:ivcap:artifact:...'."
    )
    upload_also: Optional[bool] = Field(
        False,
        description="if True, re-upload the downloaded data as a new artifact",
    )
    chunk_size_bytes: Optional[int] = Field(
        DEFAULT_ARTIFACT_CHUNK_SIZE_BYTES,
        description=(
            "size (in bytes) of each chunk read from the source artifact and, "
            "if 'upload_also' is set, immediately uploaded as a new chunk-artifact. "
            "Defaults to 1MB. Lower this to exercise chunkwise down/upload with "
            "small test artifacts, or raise it for larger artifacts that would "
            "otherwise not fit comfortably in memory as a single blob."
        ),
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
    artifact: Optional[ArtifactTester] = Field(
        None,
        description="Optionally download an artifact (and optionally re-upload it)",
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
    artifact_result: Optional[Dict] = Field(
        None, description="result of executing the 'artifact' download/upload"
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

        if req.artifact is not None:
            result.artifact_result = handle_artifact(req.artifact, ctxt)

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


class _SequentialReadStream:
    """A minimal, forward-only, sequential-read file-like adapter.

    Wraps a byte-chunk iterator (e.g. ``Artifact.as_stream()``) so it can be
    handed directly to ``ivcap.upload_artifact()``'s TUS-based ``io_stream``
    upload. The TUS uploader reads the stream in ``chunk_size``-sized
    pieces, issuing one PATCH request per chunk against a *single* upload
    session - so each downloaded chunk is appended straight onto the
    *same* destination artifact as soon as it arrives. Only one chunk is
    ever held in memory, no local disk is used, and exactly one new
    artifact results.

    ``tusclient`` probes the file size once via ``seek(0)``, then
    ``seek(0, SEEK_END)``, then ``tell()`` (see
    ``BaseUploader.get_file_size``/``get_file_stream``) - without any
    ``read()`` in between - and, before every chunk read, issues a
    ``seek(0)`` immediately followed by ``seek(<current offset>)`` (see
    ``BaseTusRequest.__init__``). We track whichever of "seek-to-end" or
    "seek-to-offset" was requested *last*, so ``tell()``/``read()`` always
    see the intended position even though a redundant ``seek(0)`` precedes
    both patterns. True random access is not supported - only the
    sequential access pattern tus actually performs.
    """

    def __init__(self, chunk_iter: Iterator[bytes], total_size: int):
        self._chunk_iter = chunk_iter
        self._total_size = total_size
        self._buffer = b""
        self._delivered = 0  # bytes already handed out via read()
        self._wanted_pos: int = 0
        self._at_end = False

    def seek(self, pos: int, whence: int = 0) -> int:
        if whence == os.SEEK_END:
            self._at_end = True
            return self._total_size
        if whence != os.SEEK_SET:
            raise NotImplementedError("only SEEK_SET/SEEK_END are supported")
        self._at_end = False
        self._wanted_pos = pos
        return pos

    def tell(self) -> int:
        return self._total_size if self._at_end else self._wanted_pos

    def read(self, n: int = -1) -> bytes:
        if not self._at_end and self._wanted_pos != self._delivered:
            raise ValueError(
                "_SequentialReadStream only supports sequential, forward-only "
                f"reads; requested position {self._wanted_pos} but "
                f"{self._delivered} bytes have already been delivered."
            )
        while n < 0 or len(self._buffer) < n:
            try:
                self._buffer += next(self._chunk_iter)
            except StopIteration:
                break
        if n < 0:
            data, self._buffer = self._buffer, b""
        else:
            data, self._buffer = self._buffer[:n], self._buffer[n:]
        self._delivered += len(data)
        self._wanted_pos = self._delivered
        return data


def handle_artifact(req: ArtifactTester, ctxt: JobContext) -> Dict:
    """
    Downloads the artifact identified by 'req.artifact_urn' in fixed-size
    chunks (of 'req.chunk_size_bytes' bytes, default 1MB) and, if
    'req.upload_also' is set, streams each chunk straight into a SINGLE
    new artifact - one TUS PATCH request per chunk, appended to the same
    upload session - as soon as it is downloaded.

    This "download a chunk, upload that chunk, repeat" pattern means at
    most one chunk is ever held in memory at a time - neither the full
    source artifact nor the full re-uploaded data needs to fit in memory
    or on local disk - while still producing exactly ONE resulting
    artifact (not one artifact per chunk). This is useful for
    exercising/testing the handling of artifacts too large to buffer or
    store locally: lower 'chunk_size_bytes' for many small round trips
    against a test artifact, or raise it for a genuinely huge artifact.

    Note: streaming the upload this way requires the source artifact's
    total size to be known upfront (the TUS protocol needs the total
    'Upload-Length' when the session is created). If the size is unknown,
    this falls back to buffering the full download in memory before doing
    a single, regular (non-chunked) upload.

    :param req: ArtifactTester object containing the artifact urn, upload
        flag, and chunk size.
    :return: a dict describing the downloaded artifact and, if uploaded,
        the resulting (single) artifact urn.
    """
    ivcap = ctxt.ivcap
    # 'chunk_size_bytes' is Optional, so an explicit 'null' in the request
    # would otherwise bypass the Pydantic field default - fall back here too.
    chunk_size = req.chunk_size_bytes or DEFAULT_ARTIFACT_CHUNK_SIZE_BYTES

    artifact = ivcap.get_artifact(req.artifact_urn)

    downloaded_bytes = 0
    chunk_count = 0
    uploaded_artifact_urn: Optional[str] = None

    with ctxt.report.step(
        "download_upload_artifact",
        f"Downloading artifact {req.artifact_urn} in {chunk_size}-byte chunks"
        + (" and streaming them into a new artifact" if req.upload_also else ""),
        artifact_urn=req.artifact_urn,
        chunk_size_bytes=chunk_size,
        upload_also=req.upload_also,
    ) as step:
        # as_stream(chunk_size=...) performs a streaming HTTP GET and yields
        # exactly 'chunk_size'-sized byte chunks (the last one may be
        # smaller), so only one chunk is ever buffered by the HTTP client
        # at a time.
        source_chunks = artifact.as_stream(chunk_size=chunk_size)

        def tracked_chunks() -> Iterator[bytes]:
            nonlocal downloaded_bytes, chunk_count
            for chunk in source_chunks:
                chunk_count += 1
                downloaded_bytes += len(chunk)
                step.info(
                    event={
                        "chunk": chunk_count,
                        "chunk_bytes": len(chunk),
                        "downloaded_bytes": downloaded_bytes,
                    }
                )
                yield chunk

        if req.upload_also and artifact.size and artifact.size > 0:
            # Wrap the chunk iterator in a sequential-read adapter and hand
            # it straight to upload_artifact() as a single streamed upload:
            # each chunk is appended (via one TUS PATCH request) directly
            # onto the single resulting artifact as soon as it is
            # downloaded - no full buffering, and exactly one artifact is
            # created.
            stream = _SequentialReadStream(tracked_chunks(), artifact.size)
            uploaded = ivcap.upload_artifact(
                name=artifact.name or "uploaded-artifact",
                io_stream=stream,
                content_type=artifact.mime_type or "application/octet-stream",
                content_size=artifact.size,
                chunk_size=chunk_size,
            )
            uploaded_artifact_urn = uploaded.id
        elif req.upload_also:
            # Source artifact size is unknown, so a streamed single-pass
            # TUS upload isn't possible (Upload-Length must be known up
            # front). Fall back to buffering the chunks fully in memory
            # before doing one regular upload.
            buffer = io.BytesIO()
            for chunk in tracked_chunks():
                buffer.write(chunk)
            buffer.seek(0)
            uploaded = ivcap.upload_artifact(
                name=artifact.name or "uploaded-artifact",
                io_stream=buffer,
                content_type=artifact.mime_type or "application/octet-stream",
                content_size=downloaded_bytes,
            )
            uploaded_artifact_urn = uploaded.id
        else:
            for _ in tracked_chunks():
                pass

        step.finished(
            msg=f"Downloaded {downloaded_bytes} bytes in {chunk_count} chunks",
            downloaded_bytes=downloaded_bytes,
            chunk_count=chunk_count,
        )

    result: Dict[str, Any] = {
        "artifact_urn": artifact.id,
        "name": artifact.name,
        "mime_type": artifact.mime_type,
        "downloaded_bytes": downloaded_bytes,
        "chunk_count": chunk_count,
        "chunk_size_bytes": chunk_size,
    }
    if req.upload_also:
        result["uploaded_artifact_urn"] = uploaded_artifact_urn

    return result


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
