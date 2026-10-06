# JobContext

`JobContext` is the gateway to the IVCAP platform from within your job worker function.
It is passed automatically as the second argument to every worker function and provides:

- **Job identity** — the unique ID and platform-injected authorisation token for the current job.
- **Progress & event reporting** — a pre-configured [`EventReporter`](events.md) for emitting structured step events back to the platform.
- **Full IVCAP platform access** — a lazy-initialized, pre-authenticated `IVCAP` client from the [ivcap-client](https://github.com/ivcap-works/ivcap-client-sdk-python) library for uploading/downloading artifacts, querying metadata, and calling other services.

```python
from ivcap_service import JobContext

def process_job(req: MyRequest, ctxt: JobContext) -> MyResult:
    # Identity
    logger.info(f"Processing job {ctxt.job_id}")

    # Progress reporting
    with ctxt.report.step("analysis", message="Analysing input") as step:
        result = analyse(req.data)
        step.finished(message="Analysis complete")

    # Platform access
    artifact = ctxt.ivcap.get_artifact(req.input_urn)
    with artifact.as_local_file() as path:
        data = path.read_bytes()

    return MyResult(output=result)
```

---

## Properties

### `job_id` · `str`

The platform-assigned unique identifier for this job (e.g. `urn:ivcap:job:...`).
Use this in log messages and when correlating events or results.

```python
logger.info(f"Starting job {ctxt.job_id}")
```

---

### `report` · `EventReporter`

A fully configured [`EventReporter`](events.md) instance for emitting structured progress events during execution.
The reporter uses the platform sidecar when running on IVCAP, and falls back to structured logging locally.

**Quick reference:**

```python
# Context-manager style (recommended)
with ctxt.report.step("load", message="Loading data") as step:
    data = load(req.source)
    step.info({"progress_percent": 50})   # (1)
    step.finished(message=f"Loaded {len(data)} records")

# Direct-call style (for async or conditional reporting, outside a `with` block)
ctxt.report.step_started("analysis", message="Starting analysis")
ctxt.report.step_finished("analysis", message="Done")
```

1. `step.info(...)` is a method on the step object returned by `ctxt.report.step(...)`
   (inside the `with` block), not on the `EventReporter` itself. It accepts either a raw
   `dict` (wrapped into a `GenericEvent`) or any `BaseEvent` instance.

For full details on event types, the `EventContext` step object, and custom reporters see
**[Events & Reporting API →](events.md)**

---

### `ivcap` · `IVCAP`

A lazy-initialized, pre-authenticated client from the [`ivcap-client`](https://github.com/ivcap-works/ivcap-client-sdk-python) library.
It is instantiated on first access — no credentials or configuration are required inside a platform job container.

```python
ivcap = ctxt.ivcap   # property access, no parentheses
```

The client is the primary entry point for all platform interactions:

| What you want to do | Method / starting point |
|---|---|
| Download an input artifact | `ivcap.get_artifact(urn)` |
| Upload a result artifact | `ivcap.upload_artifact(...)` |
| Attach metadata to an entity | `ivcap.add_aspect(entity, aspect)` |
| List or query existing aspects | `ivcap.list_aspects(entity=...)` |
| Call another IVCAP service | `ivcap.get_service_by_name(...)` → `.request_job(...)` |
| List available services | `ivcap.list_services(...)` |

**Working with artifacts →** [Artifacts Guide](../guides/artifacts.md)

**Calling other services →** [Service Composition Guide](../guides/service-composition.md)

---

### `job_authorization` · `str | None`

The Bearer token injected by the platform for the current job.
This is used internally by the SDK to authenticate outbound HTTP calls (via the `requests` and `httpx` monkey-patches in `context.py`) and by the `EventReporter` when posting events to the sidecar.

You rarely need to access this directly — the `ivcap` client and the HTTP instrumentation layer use it automatically.

---

## Execution flow

```mermaid
sequenceDiagram
    participant P as IVCAP Platform
    participant S as Service Worker
    participant R as EventReporter
    participant C as IVCAP Client

    P->>S: invoke worker(req, ctxt)
    S->>R: ctxt.report.step("…")
    R->>P: POST /events/{job_id}
    S->>C: ctxt.ivcap.get_artifact(…)
    C->>P: GET /artifacts/{id}
    P-->>C: artifact stream
    S->>R: step.finished(…)
    R->>P: POST /events/{job_id}
    S->>P: result (via push_result)
```

---

## API Reference

::: ivcap_service.types.JobContext
