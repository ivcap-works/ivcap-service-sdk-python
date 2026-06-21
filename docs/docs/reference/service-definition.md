# Service Definition Schema

Reference for the service definition structure.

## Service Class

The `Service` class defines your service metadata. The `contact` and `license`
fields use dedicated typed models (`ServiceContact` and `ServiceLicense`) for
clarity and type safety.

```python
from ivcap_service import Service, ServiceContact, ServiceLicense

service = Service(
    name="My Service",
    contact=ServiceContact(name="John Doe", email="john@example.com"),
    license=ServiceLicense(name="MIT", url="https://opensource.org/license/MIT"),
)
```

## ServiceContact Class

Typed model describing the service contact person.

```python
from ivcap_service import ServiceContact

contact = ServiceContact(
    name="Jane Smith",
    email="jane@example.com",
    url="https://example.com/jane",   # optional
)
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | `str` | ✅ | Full name of the contact person |
| `email` | `str` | ✅ | Email address of the contact person |
| `url` | `str \| None` | ❌ | Optional URL for the contact (e.g. profile page) |

## ServiceLicense Class

Typed model describing the service license.

```python
from ivcap_service import ServiceLicense

license = ServiceLicense(
    name="MIT",
    url="https://opensource.org/license/MIT",   # optional
)
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | `str` | ✅ | License name (e.g. MIT, Apache-2.0, proprietary) |
| `url` | `str \| None` | ❌ | Optional URL pointing to the full license text |

## Service Class Fields

### Required

- **name** (`str`) — Human-readable service name
- **contact** (`ServiceContact`) — Typed contact details (see above)

### Optional

- **version** (`str | None`) — Service version; defaults to the `VERSION` environment variable if not provided
- **license** (`ServiceLicense | None`) — Typed license information (see above)

## Complete Example

```python
import os
from ivcap_service import Service, ServiceContact, ServiceLicense

service = Service(
    name="Image Processor",
    version=os.environ.get("VERSION", "1.0.0"),
    contact=ServiceContact(
        name="Image Team",
        email="images@example.com",
    ),
    license=ServiceLicense(
        name="MIT",
        url="https://opensource.org/license/MIT",
    ),
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
