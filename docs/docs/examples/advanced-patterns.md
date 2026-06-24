# Advanced Patterns

Advanced techniques for building sophisticated IVCAP services.

## Service Composition Pipeline

Build complex workflows by composing multiple services:

```python
import time

def process_job(req: Request, ctxt: JobContext) -> Result:
    ivcap = ctxt.ivcap

    validate_svc = ivcap.get_service_by_name("validate-service")
    transform_svc = ivcap.get_service_by_name("transform-service")
    enrich_svc   = ivcap.get_service_by_name("enrich-service")

    with ctxt.report.step("validate", msg="Validating") as s:
        ValidateReq = validate_svc.request_model
        validated_job = validate_svc.request_job(ValidateReq(data=req.data), timeout=60)
        s.finished()

    with ctxt.report.step("transform", msg="Transforming") as s:
        TransformReq = transform_svc.request_model
        transformed_job = transform_svc.request_job(
            TransformReq(data=validated_job.result), timeout=120
        )
        s.finished()

    with ctxt.report.step("enrich", msg="Enriching") as s:
        EnrichReq = enrich_svc.request_model
        enriched_job = enrich_svc.request_job(
            EnrichReq(data=transformed_job.result), timeout=120
        )
        s.finished()

    return Result(result=enriched_job.result)
```

## Parallel Fan-Out

Dispatch multiple downstream jobs in parallel, then collect results:

```python
import time

def process_job(req: Request, ctxt: JobContext) -> Result:
    ivcap = ctxt.ivcap
    results = {}

    processor = ivcap.get_service_by_name("item-processor")
    ProcessorReq = processor.request_model

    # Dispatch all jobs without blocking (timeout=0)
    jobs = {
        item_id: processor.request_job(ProcessorReq(data=item), timeout=0)
        for item_id, item in enumerate(req.items)
    }

    # Poll until all finish
    completed = 0
    with ctxt.report.step("parallel_processing", msg="Waiting for parallel jobs") as step:
        while completed < len(jobs):
            for item_id, job in jobs.items():
                if item_id not in results and job.finished:
                    results[item_id] = job.result
                    completed += 1
                elif not job.finished:
                    job.refresh()

            if completed < len(jobs):
                step.info(event={"completed": completed, "total": len(jobs)})
                time.sleep(3)

        step.finished(msg=f"Completed {len(results)} jobs")

    return Result(results=results)
```

## Streaming Large Files

Handle large artifacts efficiently using `as_stream()` or `as_local_file()`:

```python
import io

def process_job(req: Request, ctxt: JobContext) -> Result:
    ivcap = ctxt.ivcap
    chunk_size = 1024 * 1024  # 1 MB

    artifact = ivcap.get_artifact(req.input_urn)

    with ctxt.report.step("process", msg="Streaming and processing") as step:
        processed_chunks = []
        bytes_processed = 0

        for chunk in artifact.as_stream():
            processed = process_chunk(chunk)
            processed_chunks.append(processed)
            bytes_processed += len(chunk)

            if bytes_processed % (10 * 1024 * 1024) == 0:  # Every 10 MB
                step.info(event={"bytes_processed": bytes_processed})

        step.finished(msg=f"Processed {bytes_processed} bytes")

    with ctxt.report.step("upload", msg="Uploading result") as step:
        final_data = b"".join(processed_chunks)
        result_artifact = ivcap.upload_artifact(
            name="processed-output.bin",
            io_stream=io.BytesIO(final_data),
            content_type="application/octet-stream",
            content_size=len(final_data),
        )
        step.finished(msg=f"Uploaded {result_artifact.id}")

    return Result(artifact_urn=result_artifact.id)
```

For very large files where you want minimal memory footprint, download directly to disk:

```python
def process_job(req: Request, ctxt: JobContext) -> Result:
    ivcap = ctxt.ivcap

    artifact = ivcap.get_artifact(req.input_urn)

    with ctxt.report.step("process", msg="Processing large file") as step:
        # as_local_file() streams the artifact to a temp file — no memory spike
        with artifact.as_local_file() as path:
            result = process_large_file(path)  # path is a pathlib.Path
        step.finished()

    return Result(result=result)
```

## Retry with Exponential Backoff

Robust error handling with exponential backoff:

```python
import time
import random
from ivcap_client.exception import IvcapApiError

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

def process_job(req: Request, ctxt: JobContext) -> Result:
    ivcap = ctxt.ivcap

    downstream = ivcap.get_service_by_name("flaky-service")
    DownstreamReq = downstream.request_model

    with ctxt.report.step("call_service", msg="Calling service with retry") as step:
        job = retry_with_backoff(
            lambda: downstream.request_job(DownstreamReq(data=req.data), timeout=60)
        )
        step.finished()

    return Result(result=job.result)
```

## Dynamic Service Discovery

Find and invoke services at runtime based on request parameters:

```python
def process_job(req: Request, ctxt: JobContext) -> Result:
    ivcap = ctxt.ivcap

    # Look up service by name from the request
    svc = ivcap.get_service_by_name(req.processor_service_name)
    SvcReq = svc.request_model

    # Inspect available parameters (useful for debugging)
    for name, param in svc.parameters.items():
        logger.debug(f"  {name}: {param.type}, optional={param.is_optional}")

    with ctxt.report.step("process", msg=f"Using {req.processor_service_name}") as step:
        job = svc.request_job(SvcReq(data=req.data), timeout=300)
        step.finished()

    return Result(result=job.result)
```

## Conditional Processing

Branch to different services based on input type or size:

```python
def process_job(req: Request, ctxt: JobContext) -> Result:
    ivcap = ctxt.ivcap

    if req.type == "small":
        svc_name = "fast-processor"
    elif req.type == "large":
        svc_name = "powerful-processor"
    else:
        svc_name = "default-processor"

    svc = ivcap.get_service_by_name(svc_name)
    SvcReq = svc.request_model

    with ctxt.report.step("process", msg=f"Using {svc_name}") as step:
        job = svc.request_job(SvcReq(data=req.data), timeout=300)
        step.finished()

    return Result(result=job.result)
```

## Caching Strategy

Implement in-process caching to avoid redundant computation across jobs:

```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=100)
def get_cached_model(model_id: str):
    """Load model once per process — reused across jobs."""
    return load_model(model_id)

result_cache: dict = {}

def process_job(req: Request, ctxt: JobContext) -> Result:
    # Check in-memory cache
    input_hash = hashlib.md5(req.data).hexdigest()
    if input_hash in result_cache:
        logger.info("Cache hit!")
        return Result(result=result_cache[input_hash])

    # Process
    with ctxt.report.step("process", msg="Processing") as step:
        model = get_cached_model(req.model_id)
        result = model.predict(req.data)
        step.finished()

    # Cache for future jobs
    result_cache[input_hash] = result

    return Result(result=result)
```

## See Also

- [Service Composition Guide](../guides/service-composition.md)
- [Artifacts Guide](../guides/artifacts.md)
- [Job Processing Guide](../guides/job-processing.md)
- [Best Practices](../guides/best-practices.md)
