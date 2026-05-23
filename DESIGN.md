# Design: `ivcap_service` (IVCAP Service SDK for Python)

This repository provides a small SDK for implementing **IVCAP services** in Python.

At its core, you implement **one worker function** that:

* takes a **Pydantic** `BaseModel` as input
* returns a **Pydantic** `BaseModel` (or a small set of other supported result types)

The SDK then provides:

* a **runtime** to execute that worker inside an IVCAP “batch service” container
* **service + tool descriptions** to support agent discovery/usage
* a **sidecar protocol** to fetch jobs, push results, and report events
* optional **context propagation** (job id + auth) into outbound `requests`/`httpx` calls
* optional **OpenTelemetry** instrumentation hooks

See `examples/test-batch/` for an end-to-end example.

---

## Goals / non-goals

### Goals

* Make it easy to turn a Python function into an IVCAP-executable service.
* Keep the service authoring model simple (define models + one function).
* Provide machine-readable descriptions for agents and orchestration.
* Integrate with the IVCAP “sidecar” for job execution, result delivery, and progress events.

### Non-goals

* This SDK **does not** implement an HTTP server that directly exposes endpoints like `POST /`.
  Instead, it implements a **batch worker** that **polls a sidecar** for work.
  Any platform-facing HTTP endpoints (e.g. “submit job”) are provided by the IVCAP platform,
  not by this library.

---

## Key concepts

### 1) `Service` (human-facing metadata)

`ivcap_service.service.Service` is a Pydantic model containing basic metadata:

* `name`, `version`
* `contact`
* `license`

It is used to:

* print a **service definition** (`--print-service-description`)
* label log output and tooling

Example (from `README.md` and `examples/test-batch/batch_service.py`):

```py
from ivcap_service.service import Service

service = Service(
    name="Batch service example",
    contact={"name": "Mary Doe", "email": "mary.doe@acme.au"},
    # Note: the field on the Service model is called `license`
    license={"name": "MIT", "url": "https://opensource.org/license/MIT"},
)
```

### 2) Request/Result models (your API surface)

Services define two Pydantic models:

* `Request`: the input payload schema
* `Result`: the output payload schema

The SDK uses these models for:

* validating job input (`Request(**job["in-content"])`)
* serialising successful results
* generating a machine-readable **tool definition** (`--print-tool-description`)

In many examples you’ll see a `$schema` field using an alias:

```py
class Request(BaseModel):
    jschema: str = Field("urn:sd:schema:batch-tester.request.1", alias="$schema")
    ...
```

This is optional for local execution, but is useful/expected in IVCAP deployments.

### 3) Worker function (single entry point)

The user implements one function with the shape:

```py
def worker(req: Request) -> Result:
    ...
```

Optionally, you may accept exactly **one extra argument** of type `JobContext`:

```py
from ivcap_service import JobContext

def worker(req: Request, ctxt: JobContext) -> Result:
    ...
```

The SDK detects this extra parameter and injects a `JobContext` for each job.
Any other extra parameters are rejected.

### 4) `JobContext` (runtime context)

`ivcap_service.types.JobContext` provides:

* `job_id`: the job URN
* `job_authorization`: auth token associated with the job (if provided by the sidecar)
* `report`: an `EventReporter` instance used to emit progress events
* `ivcap`: a lazily-created `ivcap_client.IVCAP` client for platform integration

This enables service code to:

* report progress/events
* fetch artifacts or call platform APIs
* propagate job identity/authorization to outbound calls

---

## Runtime model: batch worker + sidecar

The primary runtime entry point is:

* `ivcap_service.start_batch_service(service_description, worker_fn, ...)`

It runs a loop that:

1. polls the sidecar for the next job
2. validates and executes the job
3. pushes the result back to the sidecar
4. optionally reports progress/events during execution

### Sidecar base URL

The sidecar base URL is taken from:

* `IVCAP_BASE_URL`

If it is not set, the SDK will still run locally, but sidecar communication is disabled.

### Sidecar protocol (as implemented)

The SDK uses these endpoints relative to `IVCAP_BASE_URL`:

* `GET  /next_job` → fetch the next job payload
* `POST /results/{job_id}` → push the job result
* `POST /events/{job_id}` → emit progress events

The job payload is expected to look like:

```json
{
  "id": "urn:ivcap:job:...",
  "in-content-type": "application/json",
  "in-content": { "...": "..." }
}
```

The SDK currently requires:

* `in-content-type == "application/json"`

### Execution flow (high level)

```text
┌───────────────────────┐
│ start_batch_service() │
└───────────┬───────────┘
            │
            │ GET /next_job
            v
     ┌────────────┐
     │ job payload│
     └─────┬──────┘
           │ validate with Request model
           v
     ┌────────────┐
     │ worker(req)│
     │  (+ctxt)   │
     └─────┬──────┘
           │
           │ POST /events/{job_id}  (optional, during work)
           v
     ┌────────────┐
     │   result   │
     └─────┬──────┘
           │ verify/serialise
           v
   POST /results/{job_id}
```

### Result handling

The SDK accepts multiple result shapes (see `ivcap_service/ivcap.py:verify_result`):

* a Pydantic `BaseModel` → JSON (`application/json`)
* `ExecutionError` (Pydantic) → JSON error payload (`application/json` + `Is-Error: true`)
* `BinaryResult`/`IvcapResult` → returned with an explicit content-type
* `str` → `text/plain`
* `bytes` or `BinaryIO` → `application/octet-stream`
* any other JSON-serialisable Python object → JSON

Results are pushed to the sidecar with exponential backoff retries.

### Errors and failures

* Exceptions raised by the worker are caught and converted to `ExecutionError`.
* If no result is returned, an `ExecutionError(type="no-result-error")` is produced.
* If the sidecar cannot be contacted for work after retries, the process exits.

---

## Progress reporting (“events”)

The SDK defines an event model in `ivcap_service/events.py`:

* `StepStartEvent`, `StepInfoEvent`, `StepErrorEvent`, `StepFinishEvent`
* plus generic event types

Service code uses the `JobContext.report` (`EventReporter`) to emit events.
The most common pattern is a scoped step context manager:

```py
with ctxt.report.step("consume_compute", msg="...") as step:
    ...
    step.finished(msg="done")
```

At runtime, `start_batch_service()` installs `SidecarReporter`, which sends these
events to the sidecar via `POST /events/{job_id}`.

You can also override the event transport by providing a custom factory via:

* `ivcap_service.set_event_reporter_factory(...)`

---

## Context propagation for outbound HTTP

The SDK can “patch” outbound HTTP clients to propagate job context:

* adds `Ivcap-Job-Id: <job_id>`
* adds `Authorization: <job_authorization>` for “local” URLs
* optionally routes external calls via a proxy URL

This is enabled by the runtime calling:

* `ivcap_service.context.set_context(lambda: current_job_context)`

and applies to:

* `requests.Session.send`
* `httpx.Client.send` and `httpx.AsyncClient.send`

Proxying behavior is controlled by:

* `IVCAP_PROXY_URL`

When proxying, the SDK sets:

* `Ivcap-Forward-Url: <original_url>`

---

## Telemetry

If `--with-telemetry` is set and `OTEL_EXPORTER_OTLP_ENDPOINT` is configured,
the runtime will enable OpenTelemetry auto-instrumentation and attempt to
instrument `requests` and `httpx`.

---

## Service + tool descriptions (for orchestration/agents)

This SDK can print two machine-readable documents:

### Service definition

Command line flag:

* `--print-service-description`

Implementation entry points:

* `ivcap_service.service_definition.create_*_service_definition(...)`
* `ivcap_service.service_definition.print_batch_service_definition(...)`

The service definition includes controller info for batch execution (docker image,
entrypoint command, resource requirements), plus service metadata.

### Tool definition

Command line flag:

* `--print-tool-description`

Implementation entry points:

* `ivcap_service.tool_definition.create_tool_definition(...)`
* `ivcap_service.tool_definition.print_tool_definition(...)`

The tool definition includes:

* a “flattened” function signature derived from the Request model fields
* the JSON Schema for the Request model
* the docstring-based description (cleaned for agent consumption)

---

## Local development & testing

### Run a single job from a file

Use `--test-file` to execute once with an on-disk job envelope:

```bash
python batch_service.py --test-file examples/test-batch/tests/load_1.json
```

See `examples/test-batch/tests/*.json`.

### Use the example sidecar

`examples/sidecar.py` provides a minimal FastAPI-based sidecar stub implementing:

* `GET /next_job`
* `POST /results/{job_id}`

This is useful for exercising the SDK’s polling + result push logic locally.

---

## Relationship to platform-level HTTP APIs

Although this SDK itself is a batch worker (not an HTTP server), services are typically
invoked via IVCAP platform APIs.

For example, `examples/test-batch/Makefile` shows a curl call that submits a job to
the platform (URL and exact route may vary with platform versions):

```text
POST <IVCAP_URL>/.../services2/<SERVICE_ID>/jobs
```

The platform then schedules the service container and uses the sidecar protocol
documented above to deliver work to the container.

---

## Reference: example implementation

* `examples/test-batch/batch_service.py` implements:
  * `Request` + `Result` Pydantic models
  * a worker function `consume_compute(req, ctxt)`
  * progress reporting via `ctxt.report.step(...)`
  * startup via `start_batch_service(service, consume_compute)`
