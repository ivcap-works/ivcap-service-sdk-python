# Batch Service Example

A complete example of a production-ready IVCAP batch service.

## Overview

This service processes batches of text items with validation, transformation, and error handling.

## Code

```python
from pydantic import BaseModel, Field, field_validator
from ivcap_service import (
    Service, JobContext, start_batch_service,
    getLogger, logging_init
)
import time

# Initialize logging
logging_init()
logger = getLogger("batch_service")

# Define service
service = Service(
    name="Batch Text Processor",
    description="Processes batches of text with validation and transformation",
    contact={"name": "Developer", "email": "dev@example.com"},
    license_info={"name": "MIT", "url": "https://opensource.org/license/MIT"},
)

# Request schema
class Item(BaseModel):
    id: str
    text: str = Field(min_length=1, max_length=1000)

class BatchRequest(BaseModel):
    items: list[Item] = Field(min_items=1)
    uppercase: bool = Field(default=False)

# Result schema
class ProcessedItem(BaseModel):
    id: str
    original: str
    processed: str
    word_count: int

class BatchResult(BaseModel):
    items: list[ProcessedItem]
    total_processed: int
    total_time_seconds: float

# Job processor
def process_job(req: BatchRequest, ctx: JobContext) -> BatchResult:
    """Process a batch of text items."""
    logger.info(f"Processing batch with {len(req.items)} items")
    start_time = time.time()

    results = []

    # Step 1: Validate inputs
    with ctx.report.step("validate", msg="Validating inputs") as step:
        for item in req.items:
            if not item.text.strip():
                raise ValueError(f"Item {item.id}: empty text")
        step.finished(msg=f"Validated {len(req.items)} items")

    # Step 2: Process items
    with ctx.report.step("process", msg="Processing items") as step:
        for i, item in enumerate(req.items):
            # Transform
            processed_text = item.text.upper() if req.uppercase else item.text
            word_count = len(processed_text.split())

            results.append(ProcessedItem(
                id=item.id,
                original=item.text,
                processed=processed_text,
                word_count=word_count
            ))

            # Report progress
            if (i + 1) % 10 == 0:
                step.info(event={
                    "processed": i + 1,
                    "total": len(req.items),
                    "percentage": ((i + 1) / len(req.items)) * 100
                })

        step.finished(msg=f"Processed {len(results)} items")

    # Step 3: Summary
    duration = time.time() - start_time

    with ctx.report.step("summary") as step:
        step.info(event={
            "total_items": len(results),
            "duration_seconds": duration,
            "items_per_second": len(results) / duration
        })
        step.finished()

    return BatchResult(
        items=results,
        total_processed=len(results),
        total_time_seconds=duration
    )

if __name__ == "__main__":
    start_batch_service(service, process_job)
```

## Testing

Create `test_request.json`:

```json
{
    "items": [
        {"id": "1", "text": "Hello world"},
        {"id": "2", "text": "IVCAP service"},
        {"id": "3", "text": "Batch processing"}
    ],
    "uppercase": true
}
```

Test locally:

```bash
python batch_service.py --test-file test_request.json
```

Expected output:

```
Processing batch with 3 items
Validated 3 items
Processed 3 items
...
```

## Key Features

1. **Validation** — Pydantic validates request automatically
2. **Progress Tracking** — Reports progress with step events
3. **Error Handling** — Explicit error reporting
4. **Metrics** — Tracks processing time and statistics
5. **Logging** — Structured logging for debugging

## See Also

- [Job Processing Guide](../guides/job-processing.md)
- [Artifacts Guide](../guides/artifacts.md)
- [Best Practices](../guides/best-practices.md)
