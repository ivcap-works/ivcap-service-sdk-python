# Your First Service

In this guide, we'll build a complete, production-ready service that processes images.

## Project Setup

Create a new directory for your service:

```bash
mkdir image-processor
cd image-processor
```

Create a `pyproject.toml`:

```toml
[tool.poetry]
name = "image-processor"
version = "0.1.0"
description = "IVCAP service for processing images"

[tool.poetry.dependencies]
python = "^3.10"
ivcap_service = "^0.6.0"
pillow = "^10.0.0"
pydantic = "^2.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

Install dependencies:

```bash
poetry install
```

## Step 1: Define Your Service

Create `image_processor.py`:

```python
from pydantic import BaseModel, Field
from ivcap_service import Service, JobContext, start_batch_service, getLogger, logging_init

# Initialize logging
logging_init()
logger = getLogger("image_processor")

# Define your service
service = Service(
    name="Image Processor",
    description="Resize and optimize images",
    contact={"name": "Your Name", "email": "you@example.com"},
    license_info={"name": "MIT", "url": "https://opensource.org/license/MIT"},
)

# Define request schema
class ImageRequest(BaseModel):
    """Request to process an image."""
    image_artifact_id: str = Field(description="ID of artifact containing image")
    width: int = Field(default=800, description="Target width in pixels")
    height: int = Field(default=600, description="Target height in pixels")

# Define result schema
class ImageResult(BaseModel):
    """Result after processing."""
    processed_image_id: str = Field(description="ID of processed image artifact")
    original_size: dict = Field(description="Original image dimensions")
    final_size: dict = Field(description="Final image dimensions")

# Process a job
def process_job(request: ImageRequest, context: JobContext) -> ImageResult:
    """Process an image by resizing."""
    logger.info(f"Processing job {context.job_id}")

    ivcap = context.ivcap()
    if not ivcap:
        raise RuntimeError("IVCAP client not available")

    # Step 1: Download the image
    with context.report.step("download", msg="Downloading image") as step:
        logger.info(f"Downloading artifact {request.image_artifact_id}")
        image_data = ivcap.artifact(request.image_artifact_id).read()
        step.finished(msg=f"Downloaded {len(image_data)} bytes")

    # Step 2: Process the image
    with context.report.step("process", msg="Resizing image") as step:
        from PIL import Image
        import io

        # Load image
        original_image = Image.open(io.BytesIO(image_data))
        original_size = original_image.size
        logger.info(f"Original size: {original_size}")

        # Resize
        final_image = original_image.resize((request.width, request.height))
        final_size = final_image.size
        logger.info(f"Resized to: {final_size}")

        # Convert to bytes
        output_buffer = io.BytesIO()
        final_image.save(output_buffer, format="JPEG", quality=85)
        processed_data = output_buffer.getvalue()

        step.info(event={
            "original_dimensions": original_size,
            "final_dimensions": final_size,
            "bytes": len(processed_data)
        })
        step.finished(msg="Image resized")

    # Step 3: Upload the result
    with context.report.step("upload", msg="Uploading result") as step:
        result_id = ivcap.artifact_new(
            data=processed_data,
            collection_id=None,
            tags=["processed", "image"]
        )
        logger.info(f"Uploaded result: {result_id}")
        step.finished(msg=f"Uploaded: {result_id}")

    return ImageResult(
        processed_image_id=result_id,
        original_size={"width": original_size[0], "height": original_size[1]},
        final_size={"width": final_size[0], "height": final_size[1]}
    )

if __name__ == "__main__":
    start_batch_service(service, process_job)
```

## Step 2: Create Test Data

Create `test_request.json`:

```json
{
    "image_artifact_id": "urn:ivcap:artifact:test",
    "width": 400,
    "height": 300
}
```

## Step 3: Test Locally

Print the service metadata:

```bash
poetry run python image_processor.py --print-service-description
```

You should see:

```json
{
  "name": "Image Processor",
  "description": "Resize and optimize images",
  ...
}
```

## Step 4: Dockerize Your Service

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml poetry.lock* ./
RUN pip install poetry && \
    poetry install --no-dev --no-root

# Copy service code
COPY image_processor.py .

# Run the service
ENTRYPOINT ["poetry", "run", "python", "image_processor.py"]
```

Build the image:

```bash
docker build -t image-processor:latest .
```

## Step 5: Register with IVCAP

```bash
# Get the service definition
docker run image-processor:latest --print-service-description > service.json

# Register with IVCAP
ivcap service register service.json
```

## Next Steps

- **[Job Processing Guide](../guides/job-processing.md)** — Learn advanced patterns
- **[Artifact Management](../guides/artifacts.md)** — Work with files
- **[Error Handling](../guides/error-handling.md)** — Robust services
- **[Deployment](../guides/deployment.md)** — Production setup
- **[Best Practices](../guides/best-practices.md)** — Pro tips

## Common Extensions

### Add More Parameters

```python
class ImageRequest(BaseModel):
    image_artifact_id: str
    width: int = 800
    height: int = 600
    quality: int = Field(default=85, ge=1, le=100)
    format: str = Field(default="JPEG", description="Output format: JPEG, PNG, etc")
```

### Parallel Processing

```python
import concurrent.futures

def process_batch(requests, context):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_single, req) for req in requests]
        results = [f.result() for f in futures]
    return results
```

### Caching

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_model(model_path):
    # Load model once, reuse for multiple jobs
    return load_model(model_path)
```

## Troubleshooting

### "No module named 'PIL'"

The Pillow package provides PIL:

```bash
poetry add pillow
```

### "IVCAP client not available"

The client is only available in the IVCAP environment. Locally, it returns None.

### Docker build fails

Ensure `poetry.lock` exists or let pip install handle dependencies:

```dockerfile
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev
```

## See Also

- [API Reference](../api/overview.md) — All classes and functions
- [Examples](../examples/batch-service.md) — More complete examples
