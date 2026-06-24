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

    logger.info(f"Processing request {ctx.request_id}")

    with ctx.report.step("processing") as step:
        logger.debug("Starting processing step")
        result = process(req)
        logger.debug("Processing complete")
        step.finished()

    return Result(result=result)
```

## OpenObserve Integration

Configure environment variables:

```bash
export OPENOBSERVE_URL="https://observe.example.com"
export OPENOBSERVE_ORG="myorg"
export OPENOBSERVE_USERNAME="service@example.com"
export OPENOBSERVE_TOKEN="<api-token>"
```

Then logs automatically export:

```python
from ivcap_service import logging_init, getLogger

logging_init()
logger = getLogger("my_service")

# Logs automatically sent to OpenObserve
logger.info("Processing started")
logger.error("Error occurred")
```

## Progress Events

Use the event system for progress tracking:

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    with ctx.report.step("processing", msg="Processing data") as step:
        # Send progress updates
        for i, item in enumerate(items):
            process_item(item)

            if i % 100 == 0:
                step.info(event={
                    "progress_percent": (i / len(items)) * 100,
                    "items_processed": i
                })

        step.finished(msg=f"Processed {len(items)} items")

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
