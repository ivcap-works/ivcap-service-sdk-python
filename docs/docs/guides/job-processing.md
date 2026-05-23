# Job Processing Guide

This guide covers the fundamentals of processing jobs in IVCAP services.

## The Job Processor Function

Every service needs a function that processes jobs:

```python
def process_job(request: MyRequest, context: JobContext) -> MyResult:
    """Process a single job."""
    # Your logic here
    return MyResult(...)
```

### Function Signature

The function **must**:
1. Accept exactly 2 parameters:
   - Request of your defined type (Pydantic BaseModel)
   - `JobContext` for job operations
2. Return your Result type (Pydantic BaseModel)
3. Can raise exceptions (automatically reported)

### Request & Result Types

Use Pydantic models for type safety:

```python
from pydantic import BaseModel, Field

class ProcessRequest(BaseModel):
    """Request to process data."""
    input_data: str = Field(description="Input to process")
    options: dict = Field(default_factory=dict, description="Options")

class ProcessResult(BaseModel):
    """Result after processing."""
    output_data: str = Field(description="Processed output")
    statistics: dict = Field(default_factory=dict, description="Stats")

def process_job(req: ProcessRequest, ctx: JobContext) -> ProcessResult:
    return ProcessResult(
        output_data=process(req.input_data),
        statistics={"items_processed": 1}
    )
```

## Accessing Job Context

The `JobContext` provides essential information and APIs:

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    # Job identifiers
    print(f"Job: {ctx.job_id}")
    print(f"Request: {ctx.request_id}")

    # Progress reporting
    with ctx.report.step("processing") as step:
        result = do_work()
        step.finished()

    # IVCAP platform access
    ivcap = ctx.ivcap()  # May be None outside IVCAP environment
    if ivcap:
        artifact = ivcap.artifact(artifact_id).read()

    return Result(result=result)
```

## Progress Reporting

Report multi-step workflows using the event system:

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    # Step 1: Validate
    with ctx.report.step("validate", msg="Validating input") as step:
        if not is_valid(req):
            raise ValueError("Invalid input")
        step.finished(msg="Validation passed")

    # Step 2: Process
    with ctx.report.step("process", msg="Processing") as step:
        result = process(req)
        step.info(event={"progress": 50})  # Send events
        step.finished(msg="Done")

    return Result(result=result)
```

### Step Lifecycle

```python
with ctx.report.step("step_name", msg="Description") as step:
    # Step started automatically

    # Send progress events
    step.info(event={"key": "value"})

    # Mark completion
    step.finished(msg="Complete")

    # Errors automatically reported on exception
```

## Error Handling

Exceptions are automatically reported:

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    try:
        result = process_data(req)
    except Exception as e:
        # Automatically reported to context
        logger.error(f"Processing failed: {e}", exc_info=True)
        raise  # Re-raise to fail the job

    return Result(result=result)
```

## Common Patterns

### Multi-Step Workflow

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    with ctx.report.step("load", msg="Loading data") as s:
        data = load(req.source)
        s.finished()

    with ctx.report.step("transform", msg="Transforming") as s:
        transformed = transform(data)
        s.finished(msg=f"Transformed {len(data)} items")

    with ctx.report.step("validate", msg="Validating") as s:
        validate(transformed)
        s.finished()

    with ctx.report.step("save", msg="Saving") as s:
        save(transformed)
        s.finished()

    return Result(status="success")
```

### Progress Tracking with Loops

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    items = load_items(req.source)
    results = []

    with ctx.report.step("processing", msg="Processing items") as step:
        for i, item in enumerate(items):
            result = process_item(item)
            results.append(result)

            # Report progress
            if i % 100 == 0:
                step.info(event={
                    "processed": i,
                    "total": len(items),
                    "percentage": (i / len(items)) * 100
                })

        step.finished(msg=f"Processed {len(items)} items")

    return Result(results=results)
```

### Batch Processing

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    items = load_items(req.source)
    batch_size = 32
    results = []

    with ctx.report.step("batching", msg="Processing in batches") as step:
        for batch_idx in range(0, len(items), batch_size):
            batch = items[batch_idx:batch_idx + batch_size]
            batch_results = process_batch(batch)
            results.extend(batch_results)

            step.info(event={
                "batch": batch_idx // batch_size,
                "items_processed": min(batch_idx + batch_size, len(items))
            })

        step.finished()

    return Result(results=results)
```

## Accessing External Data

### From Artifacts

See [Artifacts Guide](artifacts.md)

### From Environment Variables

```python
import os

def process_job(req: Request, ctx: JobContext) -> Result:
    # Application settings
    api_url = os.getenv("API_URL", "http://localhost:8000")
    api_key = os.getenv("API_KEY", "")

    # Use in processing
    result = call_api(api_url, api_key, req.data)

    return Result(result=result)
```

## Validation and Error Handling

Pydantic automatically validates request models:

```python
from pydantic import BaseModel, Field, field_validator

class Request(BaseModel):
    email: str = Field(description="User email")
    count: int = Field(ge=1, le=1000, description="Items to process")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if "@" not in v:
            raise ValueError("Invalid email")
        return v

def process_job(req: Request, ctx: JobContext) -> Result:
    # Request is already validated!
    # Invalid data causes the job to fail before process_job is called
    return Result(result=f"Processing {req.count} items for {req.email}")
```

## Performance Considerations

### Caching

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def load_model(model_path: str):
    """Load model once, reuse across jobs."""
    return load_from_disk(model_path)

def process_job(req: Request, ctx: JobContext) -> Result:
    # Model is loaded once and cached
    model = load_model("/path/to/model")
    return Result(result=model.predict(req.input))
```

### Memory Management

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    # Process in chunks to avoid memory issues
    results = []
    for chunk in iter_chunks(req.data, chunk_size=1000):
        result = process_chunk(chunk)
        results.extend(result)
        # Chunk is garbage collected

    return Result(results=results)
```

## See Also

- [JobContext API](../api/job-context.md) — Full context documentation
- [Artifacts](artifacts.md) — Working with files
- [Error Handling](error-handling.md) — Exception handling patterns
- [Examples](../examples/batch-service.md) — Complete working examples
