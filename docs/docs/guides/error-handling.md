# Error Handling Guide

Build robust services with comprehensive error handling.

## Automatic Error Reporting

Exceptions are automatically caught and reported:

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    # Any exception here is automatically reported
    result = process(req)  # If this raises, it's reported
    return Result(result=result)
```

## Manual Error Reporting

Explicitly report errors to the event system:

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    with ctx.report.step("processing") as step:
        try:
            result = process(req)
        except ValueError as e:
            step.error(e)
            logger.error(f"Invalid input: {e}")
            raise
        except Exception as e:
            step.error(e)
            logger.error(f"Unexpected error: {e}", exc_info=True)
            raise

    return Result(result=result)
```

## Try-Except Patterns

### Recover from Specific Errors

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    ivcap = ctx.ivcap()

    with ctx.report.step("download") as step:
        try:
            data = ivcap.artifact(req.artifact_id).read()
        except FileNotFoundError:
            logger.warning(f"Artifact not found: {req.artifact_id}")
            step.finished(msg="Using default data")
            data = DEFAULT_DATA
        except Exception as e:
            step.error(e)
            raise

    return Result(result=process(data))
```

### Retry Logic

```python
import time

def process_job(req: Request, ctx: JobContext) -> Result:
    ivcap = ctx.ivcap()
    max_retries = 3

    for attempt in range(max_retries):
        try:
            with ctx.report.step(f"attempt-{attempt+1}") as step:
                result = ivcap.service(service_id).run(req)
                step.finished()
                return Result(result=result)
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.warning(f"Attempt {attempt+1} failed, retrying in {wait_time}s")
                time.sleep(wait_time)
            else:
                logger.error(f"All {max_retries} attempts failed")
                raise
```

### Graceful Degradation

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    ivcap = ctx.ivcap()

    # Try to use high-quality service
    with ctx.report.step("process") as step:
        try:
            result = ivcap.service(hq_service_id).run(req)
            step.finished(msg="High-quality processing")
        except Exception as e:
            logger.warning(f"HQ service failed, using fallback: {e}")
            step.info(event={"fallback": True})
            # Use lower-quality fallback
            result = ivcap.service(fallback_service_id).run(req)
            step.finished(msg="Fallback processing")

    return Result(result=result, degraded=True)
```

## Validation Errors

Pydantic validates request models automatically:

```python
from pydantic import BaseModel, Field, field_validator

class Request(BaseModel):
    email: str
    age: int = Field(ge=0, le=150)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v

def process_job(req: Request, ctx: JobContext) -> Result:
    # Request is guaranteed to be valid
    # Invalid requests cause job to fail before this is called
    return Result(result=f"Processing {req.email}")
```

## Cleanup on Error

Use try-finally for cleanup:

```python
import tempfile
import os

def process_job(req: Request, ctx: JobContext) -> Result:
    tmp_file = None

    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_file = tmp.name
            # Use temp file...
            result = process_file(tmp_file)

    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        raise
    finally:
        # Always clean up
        if tmp_file and os.path.exists(tmp_file):
            os.unlink(tmp_file)

    return Result(result=result)
```

## Partial Success Handling

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    results = []
    errors = []

    with ctx.report.step("batch_processing") as step:
        for i, item in enumerate(req.items):
            try:
                result = process_item(item)
                results.append(result)
            except Exception as e:
                errors.append({
                    "index": i,
                    "item": item,
                    "error": str(e)
                })
                logger.warning(f"Failed to process item {i}: {e}")

        step.finished(msg=f"Processed {len(results)}/{len(req.items)} items")

    return Result(
        results=results,
        errors=errors,
        success=len(errors) == 0
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
    """Resource not available."""
    pass

def process_job(req: Request, ctx: JobContext) -> Result:
    try:
        if not validate(req):
            raise ValidationError("Invalid input")

        ivcap = ctx.ivcap()
        if not ivcap:
            raise ResourceError("IVCAP not available")

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
