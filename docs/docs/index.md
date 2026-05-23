# IVCAP Service SDK for Python

Welcome to the **IVCAP Service SDK** — a Python library for building batch services that integrate with the IVCAP data and compute platform.

This SDK simplifies development of long-running, queue-based worker services with minimal boilerplate. Focus on your business logic while the SDK handles:

- ✅ **Asynchronous job processing** with automatic error handling
- ✅ **Artifact management** — upload, download, and process files
- ✅ **Service composition** — call other IVCAP services dynamically
- ✅ **Progress reporting** — track job execution with named steps
- ✅ **Observability** — export logs and metrics to OpenObserve
- ✅ **Type safety** — fully typed with Pydantic models

## Quick Example

```python
from pydantic import BaseModel, Field
from ivcap_service import Service, JobContext, start_batch_service

service = Service(
    name="My Service",
    contact={"name": "Your Name", "email": "you@example.com"},
)

class Request(BaseModel):
    input_data: str = Field(description="Data to process")

class Result(BaseModel):
    output_data: str = Field(description="Processing result")

def process_job(req: Request, ctxt: JobContext) -> Result:
    with ctxt.report.step("processing", msg="Starting work") as step:
        result = req.input_data.upper()
        step.finished(msg="Done!")
    return Result(output_data=result)

if __name__ == "__main__":
    start_batch_service(service, process_job)
```

## Getting Started

New to IVCAP services? Start here:

1. **[Installation](getting-started/installation.md)** — Set up the SDK
2. **[Quick Start](getting-started/quick-start.md)** — Run your first service
3. **[Your First Service](getting-started/first-service.md)** — Build a complete example

## Learn by Example

Check out the [Examples](examples/batch-service.md) section for complete, working services including:

- Batch processing with error handling
- Artifact upload/download workflows
- Service composition patterns

## Core Concepts

### Job Processing
Every service processes jobs with strongly-typed inputs and outputs. Learn about:
- Request/Result models (Pydantic)
- Job context and metadata
- Progress tracking with steps

### IVCAP Platform Integration
Your service integrates with the platform through:
- Artifact management (download inputs, upload results)
- Service discovery and composition
- Metadata attachment (aspects)

### Observability
Monitor your services with:
- Structured logging (exported to OpenObserve)
- Progress events and job tracking
- OpenTelemetry distributed tracing

## Next Steps

- **Read [Guides](guides/overview.md)** for deep dives into each feature
- **Browse [API Reference](api/overview.md)** for complete class/function documentation
- **Check [Best Practices](guides/best-practices.md)** for production patterns
- **Deploy** with our [Deployment Guide](guides/deployment.md)

## Deployment

Ready to deploy? The SDK works seamlessly with Docker and the IVCAP platform.

```bash
# Test your service locally
python my_service.py --test-file test_job.json

# Print service metadata
python my_service.py --print-service-description
```

See the [Deployment Guide](guides/deployment.md) for production configurations.

## Where to Find Help

- **GitHub Issues**: [Report bugs or ask questions](https://github.com/ivcap-works/ivcap-service-sdk-python/issues)
- **Contributing**: [Contributions welcome!](community/contributing.md)
- **Code of Conduct**: [Community standards](community/conduct.md)

## License

This project is licensed under the [MIT License](../LICENSE).

---

**Happy building! 🚀**
