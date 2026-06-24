# Error Handling Guide

Build robust services with comprehensive error handling.

## Automatic Error Reporting

Exceptions are automatically caught and reported:

```python
def process_job(req: Request, ctxt: JobContext) -> Result:
    # Any exception here is automatically reported to the platform
    result = process(req)  # If this raises, it's reported as a job failure
    return Result(result=result)
```

## Manual Error Reporting

Explicitly report errors within named steps:

```python
def process_job(req: Request, ctxt: JobContext) -> Result:
    with ctxt.report.step("processing", msg="Processing") as step:
        try:
            result = process(req)
        except ValueError as e:
            logger.error(f"Invalid input: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            raise

    return Result(result=result)
```

## Try-Except Patterns

### Recover from Specific Errors

Use typed exceptions from `ivcap_client.exception` for platform-specific errors:

```python
from ivcap_client.exception import ResourceNotFound, IvcapApiError

def process_job(req: Request, ctxt: JobContext) -> Result:
    ivcap = ctxt.ivcap

    with ctxt.report.step("download", msg="Downloading artifact") as step:
        try:
            artifact = ivcap.get_artifact(req.artifact_urn)
            with artifact.as_local_file() as path:
                data = path.read_bytes()
            step.finished(msg=f"Downloaded {len(data)} bytes")
        except ResourceNotFound:
            logger.warning(f"Artifact not found: {req.artifact_urn}, using default data")
            step.finished(msg="Using default data")
            data = DEFAULT_DATA
        except IvcapApiError as e:
            logger.error(f"Platform API error [{e.status_code}]: {e}")
            raise

    return Result(result=process(data))
```

### Retry Logic

```python
import time

def process_job(req: Request, ctxt: JobContext) -> Result:
    ivcap = ctxt.ivcap
    max_retries = 3

    downstream = ivcap.get_service_by_name("my-downstream-service")
    DownstreamReq = downstream.request_model

    for attempt in range(max_retries):
        try:
            with ctxt.report.step(f"attempt-{attempt+1}", msg=f"Attempt {attempt+1}") as step:
                job = downstream.request_job(DownstreamReq(data=req.data), timeout=120)
                step.finished(msg="Succeeded")
                return Result(result=job.result)
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.warning(f"Attempt {attempt+1} failed, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
            else:
                logger.error(f"All {max_retries} attempts failed")
                raise
```

### Graceful Degradation

Try a high-quality service and fall back gracefully if it's unavailable:

```python
from ivcap_client.exception import ResourceNotFound, IvcapApiError

def process_job(req: Request, ctxt: JobContext) -> Result:
    ivcap = ctxt.ivcap

    with ctxt.report.step("process", msg="Processing") as step:
        try:
            hq_svc = ivcap.get_service_by_name("hq-processor")
            HqReq = hq_svc.request_model
            job = hq_svc.request_job(HqReq(data=req.data), timeout=120)
            result = job.result
            step.finished(msg="High-quality processing complete")
        except (ResourceNotFound, IvcapApiError) as e:
            logger.warning(f"HQ service unavailable ({e}), using fallback")
            step.info(event={"fallback": True})

            fallback_svc = ivcap.get_service_by_name("fallback-processor")
            FallbackReq = fallback_svc.request_model
            job = fallback_svc.request_job(FallbackReq(data=req.data), timeout=60)
            result = job.result
            step.finished(msg="Fallback processing complete")

    return Result(result=result)
```

## Validation Errors

Pydantic validates request models automatically:

```python
from pydantic import BaseModel, Field, field_validator
from ivcap_service import with_schema

@with_schema("urn:sd:schema:my-service.request.1")
class Request(BaseModel):
    email: str
    age: int = Field(ge=0, le=150)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v

def process_job(req: Request, ctxt: JobContext) -> Result:
    # Request is guaranteed to be valid here
    # Invalid requests cause the job to fail before this function is called
    return Result(result=f"Processing {req.email}")
```

## Cleanup on Error

Use `as_local_file()` as a context manager — temporary files are cleaned up
automatically on context exit.  For other resources, use `try/finally`:

```python
import io

def process_job(req: Request, ctxt: JobContext) -> Result:
    ivcap = ctxt.ivcap

    artifact = ivcap.get_artifact(req.input_urn)

    # as_local_file() auto-deletes the temp file on exit, even on exception
    with artifact.as_local_file() as path:
        result = process_file(path)

    return Result(result=result)
```

For non-artifact temporary resources:

```python
import tempfile, os

def process_job(req: Request, ctxt: JobContext) -> Result:
    tmp_file = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as tmp:
            tmp_file = tmp.name
            tmp.write(generate_data(req))
        result = process_file(tmp_file)
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        raise
    finally:
        if tmp_file and os.path.exists(tmp_file):
            os.unlink(tmp_file)

    return Result(result=result)
```

## Partial Success Handling

Continue processing items even when individual ones fail:

```python
def process_job(req: Request, ctxt: JobContext) -> Result:
    results = []
    errors = []

    with ctxt.report.step("batch_processing", msg="Processing batch") as step:
        for i, item in enumerate(req.items):
            try:
                result = process_item(item)
                results.append(result)
            except Exception as e:
                errors.append({
                    "index": i,
                    "item": str(item),
                    "error": str(e)
                })
                logger.warning(f"Failed to process item {i}: {e}")

        step.finished(msg=f"Processed {len(results)}/{len(req.items)} items successfully")

    return Result(
        results=results,
        errors=errors,
        success=len(errors) == 0,
    )
```

## Custom Error Types

```python
class ProcessingError(Exception):
    """Base error for processing failures."""
    pass

class ValidationError(ProcessingError):
    """Input validation failed."""
    pass

class ResourceError(ProcessingError):
    """Required resource not available."""
    pass

def process_job(req: Request, ctxt: JobContext) -> Result:
    try:
        if not validate(req):
            raise ValidationError("Invalid input data")

        return Result(result=process(req))

    except ValidationError as e:
        logger.error(f"Validation failed: {e}")
        raise
    except ResourceError as e:
        logger.error(f"Resource error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise
```

## See Also

- [Job Processing](job-processing.md) — Core patterns
- [Observability](observability.md) — Logging and monitoring
- [Best Practices](best-practices.md) — Production patterns
- [ivcap-client SDK — Error Handling](https://ivcap-works.github.io/ivcap-client-sdk-python/guides/error-handling/) — Client exception reference
