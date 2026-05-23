# Service Composition Guide

Compose multiple IVCAP services to build complex workflows.

## Overview

Service composition allows your service to call other IVCAP services:

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    ivcap = ctx.ivcap()

    # Call another service
    result = ivcap.service(service_id).run(request_data)

    return Result(result=result)
```

## Service Discovery

Find available services:

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    ivcap = ctx.ivcap()

    # Get service by ID
    service = ivcap.service("urn:ivcap:service:my_service")

    return Result()
```

## Calling Services

### Simple Invocation

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    ivcap = ctx.ivcap()

    # Call service with request data
    response = ivcap.service(service_id).run({
        "input_data": req.data,
        "options": req.options
    })

    return Result(result=response)
```

### With Error Handling

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    ivcap = ctx.ivcap()

    with ctx.report.step("call_service") as step:
        try:
            response = ivcap.service(service_id).run(request_data)
            step.finished(msg="Service completed")
        except Exception as e:
            step.error(e)
            raise

    return Result(result=response)
```

## Common Patterns

### Pipeline Composition

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    ivcap = ctx.ivcap()

    # Stage 1: Transform
    with ctx.report.step("transform") as s:
        transformed = ivcap.service(transform_service_id).run(req.data)
        s.finished()

    # Stage 2: Validate
    with ctx.report.step("validate") as s:
        validated = ivcap.service(validate_service_id).run(transformed)
        s.finished()

    # Stage 3: Enrich
    with ctx.report.step("enrich") as s:
        enriched = ivcap.service(enrich_service_id).run(validated)
        s.finished()

    return Result(result=enriched)
```

### Parallel Composition

```python
from concurrent.futures import ThreadPoolExecutor

def process_job(req: Request, ctx: JobContext) -> Result:
    ivcap = ctx.ivcap()

    tasks = [
        ("service1", {"data": req.data}),
        ("service2", {"data": req.data}),
        ("service3", {"data": req.data}),
    ]

    with ctx.report.step("parallel") as step:
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(ivcap.service(sid).run, data)
                for sid, data in tasks
            ]
            results = [f.result() for f in futures]

        step.finished(msg=f"Completed {len(results)} tasks")

    return Result(results=results)
```

### Fan-Out Pattern

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    ivcap = ctx.ivcap()
    results = []

    with ctx.report.step("fan_out") as step:
        for item in req.items:
            result = ivcap.service(process_service_id).run({
                "item": item
            })
            results.append(result)

        step.finished(msg=f"Processed {len(results)} items")

    return Result(results=results)
```

## See Also

- [Job Processing](job-processing.md) — Core patterns
- [Artifacts](artifacts.md) — File management between services
- [Error Handling](error-handling.md) — Robust error handling
