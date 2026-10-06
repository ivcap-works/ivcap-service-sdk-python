# Observability & Logging Guide

Monitor and debug your services with comprehensive logging and tracing.

## Structured Logging

Initialize logging at startup:

```python
from ivcap_service import logging_init, getLogger

logging_init()
logger = getLogger("my_service")

logger.info("Service started")
logger.warning("Warning message")
logger.error("Error occurred", exc_info=True)
```

## Job-Specific Logging

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    # Get job-specific logger
    logger = getLogger(f"job-{ctx.job_id}")

    logger.info(f"Processing job {ctx.job_id}")

    with ctx.report.step("processing") as step:
        logger.debug("Starting processing step")
        result = process(req)
        logger.debug("Processing complete")
        step.finished()

    return Result(result=result)
```

## OpenTelemetry / OpenObserve Integration

Logs, metrics, and traces are automatically exported via OTLP/HTTP as soon as
a usable OTLP endpoint can be resolved. A **plain, standard OpenTelemetry
endpoint is sufficient on its own** - no OpenObserve-specific env vars are
required:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://openobserve.example.com/api/default"
export OTEL_EXPORTER_OTLP_PROTOCOL="http/protobuf"
```

`OPENOBSERVE_*` environment variables are entirely optional and only ever
*add* extra information on top of the standard OTEL config above (auth,
stream-name routing, org/URL-derived endpoint shaping). They never gate
whether export happens:

```bash
export OPENOBSERVE_URL="https://observe.example.com"
export OPENOBSERVE_ORG="myorg"
export OPENOBSERVE_USERNAME="service@example.com"
export OPENOBSERVE_TOKEN="<api-token>"
```

If you need per-signal headers (e.g. OpenObserve's `stream-name` routing
header), use the standard OTel signal-specific variables - these take
precedence over the generic `OTEL_EXPORTER_OTLP_HEADERS` for their
respective signal:

```bash
export OTEL_EXPORTER_OTLP_TRACES_HEADERS="stream-name=default"
export OTEL_EXPORTER_OTLP_LOGS_HEADERS="stream-name=default"
export OTEL_EXPORTER_OTLP_METRICS_HEADERS="stream-name=default"
```

Once configured, logs automatically export:

```python
from ivcap_service import logging_init, getLogger

logging_init()
logger = getLogger("my_service")

# Logs automatically sent to OpenObserve / your OTLP collector
logger.info("Processing started")
logger.error("Error occurred")
```

### Tracing

Job and step spans are created automatically (tagged with `ivcap.job_id` and
`ivcap.service_id`, sourced from the `IVCAP_SERVICE_ID` env var). Outbound
`requests`/`httpx` calls are automatically instrumented as soon as an OTLP
endpoint is configured (see above) - no extra flag is needed:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://otel-collector:4318"
python my_service.py
```

Use `--without-telemetry` to suppress HTTP instrumentation while still
exporting logs/metrics via OpenObserve, or `--with-telemetry` to
force-enable it even before an endpoint is configured:

```bash
python my_service.py --without-telemetry
```

### Local testing without a sidecar

When testing locally (e.g. via `--test-file`) without a real IVCAP sidecar
reachable at `IVCAP_BASE_URL`, add `--test-without-sidecar` to silently skip
delivering events/results to the sidecar (no retries, no warnings):

```bash
python my_service.py --test-file job.json --test-without-sidecar
```

## Progress Events

Use the event system for progress tracking:

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    with ctx.report.step("processing", message="Processing data") as step:
        # Send progress updates
        for i, item in enumerate(items):
            process_item(item)

            if i % 100 == 0:
                step.info(event={
                    "progress_percent": (i / len(items)) * 100,
                    "items_processed": i
                })

        step.finished(message=f"Processed {len(items)} items")

    return Result(result=result)
```

## Error Tracking

Automatically report errors:

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    with ctx.report.step("processing") as step:
        try:
            result = process(req)
        except Exception as e:
            # Error automatically reported
            step.error(e)
            logger.error(f"Processing failed: {e}", exc_info=True)
            raise

    return Result(result=result)
```

## Metrics

Export metrics to OpenObserve:

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    import time

    start = time.time()
    result = process(req)
    duration = time.time() - start

    with ctx.report.step("metrics") as step:
        step.info(event={
            "duration_seconds": duration,
            "items_processed": len(req.items),
            "bytes_processed": len(req.data)
        })

    return Result(result=result)
```

## Best Practices

1. **Use job-specific loggers** for easier filtering
2. **Log at appropriate levels**: DEBUG, INFO, WARNING, ERROR
3. **Include context** in log messages (job ID, step, etc.)
4. **Use event system** for structured metrics
5. **Report errors** in both logging and event system

## See Also

- [Utilities API](../api/utilities.md) — Logging functions
- [Events & Reporting](../api/events.md) — Event system
- [Best Practices](best-practices.md) — Production patterns
