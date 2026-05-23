# Service Definition Schema

Reference for the service definition structure.

## Service Class

The `Service` class defines your service metadata:

```python
from ivcap_service import Service

service = Service(
    name="My Service",
    description="What my service does",
    contact={"name": "John Doe", "email": "john@example.com"},
    license_info={"name": "MIT", "url": "https://opensource.org/license/MIT"},
)
```

## Properties

### Required

- **name** (str) — Service name
- **contact** (dict) — Contact information
  - **name** (str) — Contact person name
  - **email** (str) — Contact email

### Optional

- **description** (str) — Service description
- **license_info** (dict) — License information
  - **name** (str) — License name (MIT, Apache, etc.)
  - **url** (str) — License URL
- **documentation** (str) — URL to service documentation
- **resources** (ResourceRequirements) — Resource requirements

## Example

```python
service = Service(
    name="Image Processor",
    description="Resizes and optimizes images for web",
    contact={
        "name": "Image Team",
        "email": "images@example.com"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/license/MIT"
    },
    documentation="https://docs.example.com/image-processor"
)
```

## Generated Schema

When you run:

```bash
python my_service.py --print-service-description
```

The SDK generates a JSON schema like:

```json
{
  "name": "Image Processor",
  "description": "Resizes and optimizes images for web",
  "contact": {
    "name": "Image Team",
    "email": "images@example.com"
  },
  "license": {
    "name": "MIT",
    "url": "https://opensource.org/license/MIT"
  },
  "input_schema": {
    "type": "object",
    "properties": {
      "image_id": {"type": "string"},
      "width": {"type": "integer"},
      "height": {"type": "integer"}
    },
    "required": ["image_id"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "processed_id": {"type": "string"}
    }
  }
}
```

This schema is used by IVCAP for service discovery and validation.

## See Also

- [Service API](../api/service.md)
- [Job Processing](../guides/job-processing.md)
