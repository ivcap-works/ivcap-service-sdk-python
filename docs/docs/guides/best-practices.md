# Best Practices Guide

Build production-quality IVCAP services with these patterns.

## Code Organization

### Structure Your Service

```
my-service/
├── src/
│   ├── __init__.py
│   ├── service.py          # Service definition & entry point
│   ├── processor.py        # Job processing logic
│   ├── models/
│   │   ├── request.py      # Request schemas
│   │   └── result.py       # Result schemas
│   └── utils/
│       ├── __init__.py
│       ├── artifacts.py    # Artifact utilities
│       ├── logger.py       # Logging setup
│       └── validators.py   # Custom validators
├── tests/
│   ├── test_processor.py
│   └── test_models.py
├── pyproject.toml
├── Dockerfile
└── README.md
```

### Separate Concerns

```python
# service.py
from src.processor import process_job
from src.models import RequestSchema, ResultSchema

service = Service(name="My Service", ...)

if __name__ == "__main__":
    start_batch_service(service, process_job)

# processor.py
from src.models import RequestSchema, ResultSchema
from src.utils import validate_input, process_data

def process_job(req: RequestSchema, ctx: JobContext) -> ResultSchema:
    validate_input(req)
    result = process_data(req.data)
    return ResultSchema(result=result)
```

## Testing

### Unit Tests

```python
# tests/test_processor.py
from src.processor import process_job
from src.models import RequestSchema, ResultSchema
import pytest

def test_process_job_basic():
    req = RequestSchema(data="test")
    # Mock the context
    result = process_job(req, mock_context)
    assert isinstance(result, ResultSchema)
    assert result.result == "TEST"

def test_process_job_invalid_input():
    with pytest.raises(ValueError):
        req = RequestSchema(data="")
        result = process_job(req, mock_context)
```

### Integration Tests

```python
# tests/test_integration.py
def test_service_with_local_file():
    """Test service with actual test data."""
    import json
    with open("tests/test_request.json") as f:
        req_data = json.load(f)

    # Create context
    ctx = create_test_context()

    # Process
    result = process_job_from_dict(req_data, ctx)

    # Verify
    assert result["status"] == "success"
```

## Performance Optimization

### Caching

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def load_model(model_path: str):
    """Load ML model once, reuse."""
    return torch.load(model_path)

def process_job(req: Request, ctx: JobContext) -> Result:
    model = load_model("/path/to/model")
    prediction = model.predict(req.data)
    return Result(prediction=prediction)
```

### Batch Processing

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    items = req.items
    batch_size = 32
    results = []

    with ctx.report.step("processing") as step:
        for i in range(0, len(items), batch_size):
            batch = items[i:i+batch_size]
            batch_results = process_batch(batch)
            results.extend(batch_results)

    return Result(results=results)
```

### Memory Management

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    # Process in chunks instead of loading all
    results = []

    with ctx.report.step("processing") as step:
        for chunk in iter_chunks(req.data, chunk_size=10_000):
            result = process_chunk(chunk)
            results.append(result)
            # Chunk is garbage collected automatically

    return Result(results=results)
```

## Error Handling Best Practices

1. **Fail fast** — Detect invalid input early
2. **Log context** — Include relevant information
3. **Graceful degradation** — Use fallbacks when possible
4. **Report progress** — Even if failing, report where

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    # 1. Validate early
    if not validate(req):
        raise ValueError("Invalid input")

    try:
        with ctx.report.step("processing") as step:
            # 2. Include context in logs
            logger = getLogger(f"job-{ctx.job_id}")
            logger.info("Starting processing")

            result = process(req)
            step.finished()
    except Exception as e:
        # 3. Report where we failed
        logger.error(f"Processing failed: {e}", exc_info=True)
        raise

    return Result(result=result)
```

## Documentation Best Practices

### Docstring Standards

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    """
    Process a batch of data items.

    This service:
    - Validates input format
    - Applies transformation
    - Returns results

    Args:
        req: Request containing items to process
        ctx: Job context for progress and platform access

    Returns:
        Result with processed items

    Raises:
        ValueError: If input validation fails
    """
    # Implementation...
```

### Service Documentation

```python
service = Service(
    name="Data Processor",
    description="Transforms and validates data items. "
                "Supports CSV and JSON input formats.",
    contact={"name": "Support Team", "email": "support@example.com"},
    license_info={"name": "MIT", "url": "https://opensource.org/license/MIT"},
    documentation="https://docs.example.com/data-processor"
)
```

## Monitoring Best Practices

### Log at Appropriate Levels

```python
logger.debug("Variable x = 5")  # Development
logger.info("Job started")       # Important milestones
logger.warning("Falling back")   # Unexpected but recoverable
logger.error("Processing failed") # Errors
```

### Include Context in Events

```python
with ctx.report.step("processing") as step:
    step.info(event={
        "job_id": ctx.job_id,
        "stage": "validation",
        "items_count": len(items),
        "timestamp": datetime.now().isoformat()
    })
```

## Configuration Best Practices

### Use Environment Variables

```python
import os

# Good: Use environment variables
api_url = os.getenv("API_URL", "http://localhost:8000")
timeout = int(os.getenv("API_TIMEOUT", "30"))

# Bad: Hardcode values
api_url = "http://production.example.com"
```

### Validate Configuration

```python
def get_config():
    config = {
        "api_url": os.getenv("API_URL"),
        "api_key": os.getenv("API_KEY"),
    }

    # Validate required settings
    if not config["api_key"]:
        raise ValueError("API_KEY environment variable not set")

    return config
```

## Security Best Practices

1. **Never hardcode secrets** — Use environment variables or secret manager
2. **Validate input** — Use Pydantic validation
3. **Sanitize output** — Don't leak sensitive information
4. **Use HTTPS** — For all external communication

```python
from ivcap_service import get_secret

def process_job(req: Request, ctx: JobContext) -> Result:
    # Good: Get from secret manager
    api_key = get_secret("external_api_key")

    # Good: Validate input with Pydantic
    # Automatically validates req type

    # Bad: Don't log secrets
    logger.info(f"Using API key: {api_key}")

    # Good: Log masked version
    logger.info("Using API key: ****")
```

## Common Pitfalls

### ❌ Don't: Store State Between Jobs

```python
# BAD - State persists between jobs
shared_state = {}

def process_job(req: Request, ctx: JobContext) -> Result:
    shared_state["count"] = shared_state.get("count", 0) + 1
```

### ✅ Do: Keep Jobs Stateless

```python
# GOOD - Each job is independent
def process_job(req: Request, ctx: JobContext) -> Result:
    count = len(req.items)
    return Result(count=count)
```

### ❌ Don't: Ignore Exceptions

```python
# BAD
try:
    result = process(req)
except:
    pass  # Silent failure
```

### ✅ Do: Handle and Report Errors

```python
# GOOD
try:
    result = process(req)
except Exception as e:
    logger.error(f"Processing failed: {e}")
    raise
```

## See Also

- [Job Processing](job-processing.md) — Core patterns
- [Deployment](deployment.md) — Production setup
- [Error Handling](error-handling.md) — Robust error handling
