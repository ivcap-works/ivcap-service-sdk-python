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
from ivcap_service.service import Service, ServiceContact, ServiceLicense

service = Service(
    name="Batch service example",
    contact=ServiceContact(name="Mary Doe", email="mary.doe@acme.au"),
    license=ServiceLicense(name="MIT", url="https://opensource.org/license/MIT"),
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

Use the `@with_schema` decorator to attach a `$schema` URN to a Pydantic model:

```py
from ivcap_service import with_schema

@with_schema("urn:sd:schema:batch-tester.request.1")
class Request(BaseModel):
    ...
```

This injects the `$schema` field automatically and is required for IVCAP deployments. Do **not** add a manual `jschema` field with `alias="$schema"`.

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

### Disabling sidecar delivery for local testing

Even with `IVCAP_BASE_URL` set (e.g. to run through `_job_span`/OpenObserve
code paths that check for its presence), you may want to run against a
non-existent/unreachable sidecar - for example when testing a locally-built
Docker image without an actual IVCAP platform behind it. In that scenario,
`push_result()` and `SidecarReporter` will otherwise retry with exponential
backoff (up to `MAX_DELIVER_RESULT_ATTEMPTS`/`MAX_REQUEST_JOB_ATTEMPTS`
times) and log warnings for every failed attempt.

The `--test-without-sidecar` CLI flag (typically combined with `--test-file`)
disables this: it calls `ivcap_service.ivcap.set_sidecar_delivery_disabled(True)`
during startup, which makes `push_result()` and `SidecarReporter._send()`
silently skip the actual HTTP call - no retries, no warnings. A locally
registered `result_callback` (via `set_result_callback()`) is still invoked,
since that is not "delivery to the sidecar". This can also be toggled
programmatically via `ivcap_service.set_sidecar_delivery_disabled()` /
`ivcap_service.is_sidecar_delivery_disabled()`.

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
* injects the current OTEL trace context (W3C `traceparent`/`tracestate`
  headers, via `opentelemetry.propagate.inject()`) so downstream services
  can continue the same trace

The trace-context injection happens unconditionally (best-effort, a no-op if
`opentelemetry` isn't installed or there's no active span) - it does **not**
require `--with-telemetry`/`OTEL_EXPORTER_OTLP_ENDPOINT` to be configured, nor
does it depend on `RequestsInstrumentor`/`HTTPXClientInstrumentor` being
installed via `otel_instrument()`. This matters because job/step spans
(`service.py::_job_span`, `events.py::EventContext`) are created whenever the
`opentelemetry` package is importable, independent of whether HTTP
auto-instrumentation is enabled; without this, calls made from inside a job
(including those routed through the sidecar/proxy) would silently break trace
continuity whenever `otel_instrument()` wasn't invoked. Calls to the OTEL
collector endpoint itself are excluded, to avoid tracing the export pipeline.

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
instrument `requests` and `httpx`. Both instrumentors (and the job/step spans
created by the SDK) check `is_instrumented_by_opentelemetry` /
`get_tracer_provider()` first, so re-running against a process that was
already auto-instrumented by an external `opentelemetry-instrument` wrapper
is a safe no-op rather than emitting spurious "already instrumented" warnings.

### Job/step spans

Every job fetched via `GET /next_job` is wrapped in an `ivcap.job` span
(see `service.py::_job_span`), tagged with:

* `ivcap.job_id` - the job's URN
* `ivcap.service_id` - this service's URN, sourced from `IVCAP_SERVICE_ID`
  (constant across all jobs handled by this service instance)
* `ivcap.ok` / `ivcap.error_type` / `ivcap.error` - outcome, set once the job
  finishes

`ctxt.report.step(...)` creates a child `ivcap.event:<name>` span
(see `events.py::EventContext`) tagged with the same `ivcap.job_id` and
`ivcap.service_id`, plus `ivcap.event_name`.

Any extra keyword arguments passed to `report.step(name, message, **kwargs)`
or `ectxt.finished(message, **kwargs)` are set as `ivcap.event.<key>` span
attributes (in addition to being included in the emitted event's JSON
payload), best-effort:

```python
with ctxt.report.step(
    "consume_compute",
    f"Consuming CPU for {duration_seconds}s at {target_cpu_percent}%",
    duration_seconds=duration_seconds,
    target_cpu_percent=target_cpu_percent,
) as ectxt:
    ...
    ectxt.finished(msg=msg, run_time=run_time)
```

produces span attributes `ivcap.event.duration_seconds`,
`ivcap.event.target_cpu_percent`, `ivcap.event.message`, `ivcap.event.msg`,
`ivcap.event.run_time`. Only OTel-representable values are set (`str`,
`bool`, `int`, `float`, or a homogeneously-typed list/tuple of those);
anything else (dicts, `None`, mixed-type lists, arbitrary objects) is
silently skipped rather than raising, since span attribute creation must
never break job execution.

### Enabling OpenObserve export - plain OTEL_* vars are sufficient

`init_openobserve_from_env()` / `load_openobserve_config_from_env()`
(`openobserve.py`) enable export implicitly as soon as a usable OTLP
endpoint can be resolved, from *either* a standard `OTEL_EXPORTER_OTLP_ENDPOINT`
*or* OpenObserve-specific config (`OPENOBSERVE_URL` / `OPENOBSERVE_OTLP_ENDPOINT`).
`OPENOBSERVE_ENABLED` is only needed to force-enable (with no endpoint - this
raises an error) or force-disable (even with an endpoint present). It is
**never** required just to turn export on: setting only
`OTEL_EXPORTER_OTLP_ENDPOINT` (+ optionally `OTEL_EXPORTER_OTLP_PROTOCOL` and
the signal-specific `OTEL_EXPORTER_OTLP_{LOGS,METRICS,TRACES}_HEADERS`) is
sufficient on its own. `OPENOBSERVE_*` variables only ever *add* extra
information on top (auth header construction, `stream-name` header
injection, org/URL-derived `/api/<org>` endpoint shaping) - they never gate
whether export happens at all.

Header resolution also honours the standard OTel signal-specific header
variables (`OTEL_EXPORTER_OTLP_LOGS_HEADERS`, `_METRICS_HEADERS`,
`_TRACES_HEADERS`), layering them on top of the generic
`OTEL_EXPORTER_OTLP_HEADERS` for their respective signal - matching standard
OTel semantics where the signal-specific variable overrides the generic one.

### OpenObserve export vs. externally-installed providers

`init_openobserve_from_env()` (`openobserve.py`) installs OTLP exporters for
logs, metrics and traces. A subtlety here: OpenTelemetry's global providers
(`TracerProvider`, `MeterProvider`, `LoggerProvider`) can each only be
installed **once** per process - `opentelemetry.trace.set_tracer_provider()`
(and the metrics/logs equivalents) silently ignore any further call once a
provider is already set, only logging a warning. If the process is launched
under an external auto-instrumentation wrapper (recognisable via
`OTEL_SERVICE_NAME` / `OTEL_EXPORTER_OTLP_*` env vars being pre-set by that
wrapper), a provider will already be active by the time this SDK code runs.

To avoid silently dropping the OpenObserve exporter in that case:

* **Traces**: `_init_traces()` detects an already-active `TracerProvider` and
  attaches its `BatchSpanProcessor`/`OTLPSpanExporter` to it via
  `add_span_processor()`, instead of trying (and failing) to install a new
  provider.
* **Logs**: `_init_logs()` is unaffected by this problem because
  `LoggingHandler` is constructed with an explicit `logger_provider=` and
  holds a direct reference to it, independent of the global registry.
* **Metrics**: the SDK's `MeterProvider` has no public API to attach an
  additional `MetricReader` after construction. If a `MeterProvider` is
  already active, `_init_metrics()` logs a warning rather than silently
  doing nothing, since there is no reliable workaround.

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

* `examples/test-batch/batch_service.py` wires up the service and starts it via
  `start_batch_service(service, process_job)`.
* `ivcap_service/testkit/` implements the actual business logic. It lives in the
  installable `ivcap_service` package (rather than under `examples/`) so it can be
  imported and reused/tested from other projects (e.g. the `ivcap-lambda` SDK) via
  `from ivcap_service.testkit import ...`, without pulling in the service-bootstrap
  code. It is a package with one module per concern, wired back together in
  `__init__.py`:
  * `models.py` - `Request` + `Result` (and nested) Pydantic models
  * `__init__.py` - the general worker function `process_job(req, ctxt)` that
    dispatches to whichever optional sub-tests are present in the request
    (none are mandatory), and re-exports the public symbols below
    * `consume_compute.py` - `consume_compute(req, ctxt)` - CPU load test (`req.consume_cpu`)
    * `call.py` - `make_request(req, ctxt)` - generic HTTP call (`req.call`)
    * `llm.py` - `completion(req)` - LLM completion call (`req.llm`)
    * `artifact.py` - `handle_artifact(req, ctxt)` - artifact download/upload (`req.artifact`)
  * progress reporting via `ctxt.report.step(...)`
