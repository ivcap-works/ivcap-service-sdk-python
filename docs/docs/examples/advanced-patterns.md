# Advanced Patterns

Advanced techniques for building sophisticated IVCAP services.

## Service Composition Pipeline

Build complex workflows by composing multiple services:

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    ivcap = ctx.ivcap()

    with ctx.report.step("validate") as s:
        validated = ivcap.service("validate-service").run(req.data)
        s.finished()

    with ctx.report.step("transform") as s:
        transformed = ivcap.service("transform-service").run(validated)
        s.finished()

    with ctx.report.step("enrich") as s:
        enriched = ivcap.service("enrich-service").run(transformed)
        s.finished()

    return Result(result=enriched)
```

## Parallel Processing

Process multiple items in parallel:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def process_job(req: Request, ctx: JobContext) -> Result:
    ivcap = ctx.ivcap()
    results = {}

    with ctx.report.step("parallel_processing") as step:
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(
                    ivcap.service(service_id).run, item
                ): item_id
                for item_id, item in enumerate(req.items)
            }

            completed = 0
            for future in as_completed(futures):
                item_id = futures[future]
                results[item_id] = future.result()
                completed += 1

                if completed % 10 == 0:
                    step.info(event={"completed": completed})

        step.finished(msg=f"Completed {len(results)} items")

    return Result(results=results)
```

## Streaming Large Files

Handle large files efficiently:

```python
import io

def process_job(req: Request, ctx: JobContext) -> Result:
    ivcap = ctx.ivcap()
    chunk_size = 1024 * 1024  # 1MB chunks

    with ctx.report.step("download") as step:
        artifact = ivcap.artifact(req.input_id)
        step.finished()

    with ctx.report.step("process") as step:
        processed_chunks = []
        bytes_processed = 0

        for chunk in artifact.iter_content(chunk_size=chunk_size):
            processed = process_chunk(chunk)
            processed_chunks.append(processed)
            bytes_processed += len(chunk)

            if bytes_processed % (10 * 1024 * 1024) == 0:  # Every 10MB
                step.info(event={"bytes_processed": bytes_processed})

        step.finished()

    with ctx.report.step("upload") as step:
        final_data = b"".join(processed_chunks)
        artifact_id = ivcap.artifact_new(data=final_data)
        step.finished()

    return Result(artifact_id=artifact_id)
```

## Retry with Exponential Backoff

Robust error handling with exponential backoff:

```python
import time
import random

def retry_with_backoff(func, max_retries=3, base_wait=1):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait_time = base_wait * (2 ** attempt) + random.uniform(0, 1)
            logger.warning(f"Attempt {attempt+1} failed, retrying in {wait_time:.1f}s: {e}")
            time.sleep(wait_time)

def process_job(req: Request, ctx: JobContext) -> Result:
    ivcap = ctx.ivcap()

    with ctx.report.step("call_service") as step:
        result = retry_with_backoff(
            lambda: ivcap.service(service_id).run(req)
        )
        step.finished()

    return Result(result=result)
```

## Dynamic Service Discovery

Find and invoke services dynamically:

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    ivcap = ctx.ivcap()

    # Find service by name
    service_name = req.processor_type
    service_id = ivcap.service_by_name(service_name)

    if not service_id:
        raise ValueError(f"Service not found: {service_name}")

    with ctx.report.step("process") as step:
        result = ivcap.service(service_id).run(req.data)
        step.finished()

    return Result(result=result)
```

## Conditional Processing

Branch logic based on input:

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    ivcap = ctx.ivcap()

    if req.type == "small":
        service = "fast-processor"
    elif req.type == "large":
        service = "powerful-processor"
    else:
        service = "default-processor"

    with ctx.report.step("process") as step:
        result = ivcap.service(service).run(req.data)
        step.finished()

    return Result(result=result)
```

## Caching Strategy

Implement intelligent caching:

```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=100)
def get_cached_model(model_id: str):
    """Load model with caching."""
    return load_model(model_id)

def get_input_hash(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()

result_cache = {}

def process_job(req: Request, ctx: JobContext) -> Result:
    # Check cache
    input_hash = get_input_hash(req.data)
    if input_hash in result_cache:
        logger.info("Cache hit!")
        return Result(result=result_cache[input_hash])

    # Process
    with ctx.report.step("process") as step:
        model = get_cached_model(req.model_id)
        result = model.predict(req.data)
        step.finished()

    # Cache result
    result_cache[input_hash] = result

    return Result(result=result)
```

## See Also

- [Service Composition Guide](../guides/service-composition.md)
- [Job Processing Guide](../guides/job-processing.md)
- [Best Practices](../guides/best-practices.md)
