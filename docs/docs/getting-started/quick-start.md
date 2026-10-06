# Quick Start

Get a working IVCAP service running in 5 minutes.

## 1. Install the SDK

```bash
pip install ivcap_service
```

## 2. Create Your Service

Save this as `my_service.py`:

```python
from pydantic import BaseModel, Field
from ivcap_service import (
    Service, ServiceContact, ServiceLicense,
    JobContext, start_batch_service, getLogger, logging_init, with_schema,
)

# Initialize logging
logging_init()
logger = getLogger("my_service")

# Define your service
service = Service(
    name="My First Service",
    contact=ServiceContact(name="Your Name", email="you@example.com"),
    license=ServiceLicense(name="MIT", url="https://opensource.org/license/MIT"),
)

# Define request schema
@with_schema("urn:sd:schema:my_service.request.1")
class TextRequest(BaseModel):
    text: str = Field(description="Text to convert to uppercase")

# Define result schema
@with_schema("urn:sd:schema:my_service.result.1")
class TextResult(BaseModel):
    uppercase_text: str = Field(description="Converted text")

# Process a job
def process_job(request: TextRequest, context: JobContext) -> TextResult:
    """Convert input text to uppercase."""
    logger.info(f"Processing job {context.job_id}")

    with context.report.step("converting", message="Converting text...") as step:
        result = request.text.upper()
        step.finished(message=f"Converted: {request.text}")

    return TextResult(uppercase_text=result)

# Run the service
if __name__ == "__main__":
    start_batch_service(service, process_job)
```

## 3. Test Your Service

Test it locally with a JSON file. The SDK expects a job "envelope" with an
`id`, `in-content-type`, and `in-content` (the actual request payload, which
must include the `$schema` matching your `Request` model). Create
`test_request.json`:

```json
{
    "id": "urn:ivcap:job:test-1",
    "in-content-type": "application/json",
    "in-content": {
        "$schema": "urn:sd:schema:my_service.request.1",
        "text": "hello world"
    }
}
```

Run the test:

```bash
python my_service.py --test-file test_request.json
```

You should see:
```json
{
  "$schema": "urn:sd:schema:my_service.result.1",
  "uppercase_text": "HELLO WORLD"
}
```

## 4. Print Service Metadata

View the service definition that will be registered with IVCAP:

```bash
python my_service.py --print-service-description
```

## 5. Run the Service

To run the service (waiting for jobs from IVCAP):

```bash
python my_service.py
```

The service will start and wait for jobs. In production, this runs in a container orchestrated by IVCAP.

## Next Steps

- **[Your First Service](first-service.md)** — Build a more complete example
- **[Job Processing Guide](../guides/job-processing.md)** — Learn advanced patterns
- **[Examples](../examples/batch-service.md)** — See production-ready code
- **[API Reference](../api/overview.md)** — Complete class/function documentation

## Common Patterns

### Accessing Job Metadata

```python
def process_job(request: TextRequest, context: JobContext) -> TextResult:
    print(f"Job ID: {context.job_id}")
    # More in JobContext API...
```

### Reporting Progress

```python
with context.report.step("step1") as step:
    # Do work...
    step.finished(message="Completed step 1")

with context.report.step("step2") as step:
    # Do more work...
    step.info({"key": "value"})  # Send an info event
    step.finished()
```

### Error Handling

```python
def process_job(request: TextRequest, context: JobContext) -> TextResult:
    try:
        # Process...
        pass
    except Exception as e:
        # Errors raised inside a `with context.report.step(...)` block are
        # reported automatically; call `step.error(e)` explicitly if you need
        # to report one without letting it propagate out of the `with` block.
        logger.error(f"Processing failed: {e}", exc_info=True)
        raise
```

## Troubleshooting

### "No module named 'ivcap_service'"
See [Installation](installation.md#troubleshooting)

### Service won't run
Check that you have the `process_job` function signature correct:
- Takes `(request_type, JobContext)`
- Returns `result_type`

### Test file not found
Make sure the test file exists and is in the correct location.

For more help, see [Best Practices](../guides/best-practices.md).
