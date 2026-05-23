# SKILLS.md: Building IVCAP Batch Services

This document provides comprehensive instructions for agents (skills) on how to use the ivcap-service library to build IVCAP batch services.

## Overview

The ivcap-service Python library simplifies development of batch services for the IVCAP platform. A batch service is a long-running worker that processes jobs in a queue-based manner, with each job being independently executed.

## Quick Start Example

The `examples/test-batch/batch_service.py` file demonstrates a complete batch service implementation. Refer to this file for a working example of all concepts described below.

## Table of Contents

1. [Architecture](#architecture)
2. [Step-by-Step Guide](#step-by-step-guide)
   - [1. Import Required Components](#1-import-required-components)
   - [2. Initialize Logging](#2-initialize-logging)
   - [3. Define the Service](#3-define-the-service)
   - [4. Define the Request Model](#4-define-the-request-model)
   - [5. Define the Result Model](#5-define-the-result-model)
   - [6. Implement the Worker Function](#6-implement-the-worker-function)
   - [7. Using JobContext](#7-using-jobcontext)
   - [8. Interacting with IVCAP Services via context.ivcap](#8-interacting-with-ivcap-services-via-contextivcap)
   - [9. Error Handling](#9-error-handling)
   - [10. Logging](#10-logging)
   - [11. Start the Service](#11-start-the-service)
   - [12. Testing](#12-testing)
   - [13. Service Definition and Metadata](#13-service-definition-and-metadata)
3. [Advanced Features](#advanced-features)
   - [Environment Variables](#environment-variables)
   - [Logging to OpenObserve](#logging-to-openobserve)
   - [OpenTelemetry Support](#opentelemetry-support)
   - [Custom Arguments](#custom-arguments)
4. [Project Structure](#project-structure)
5. [Docker Deployment](#docker-deployment)
6. [Complete Example Breakdown](#complete-example-breakdown)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)
9. [Related Documentation](#related-documentation)

## Architecture

An IVCAP batch service consists of:

1. **Service Description** - Metadata about the service (name, version, contact, license)
2. **Request Model** - Pydantic model defining input parameters
3. **Result Model** - Pydantic model defining output/result structure
4. **Worker Function** - The main function that processes each job
5. **Entry Point** - Bootstrap code that starts the service

### Execution Flow

```
IVCAP Platform
    ↓
Service Instance (waiting for work)
    ↓ (fetches next job)
Worker Function (processes job)
    ↓
Result/Error (reported back to platform)
    ↓
Repeat (wait for next job)
```

## Step-by-Step Guide

### 1. Import Required Components

```python
from pydantic import BaseModel, Field
from ivcap_service import (
    Service,
    JobContext,
    getLogger,
    logging_init,
    start_batch_service,
)
```

Key imports:
- `Service` - Service descriptor class
- `JobContext` - Context object passed to worker function (optional)
- `getLogger` - Structured logging
- `logging_init` - Initialize logging system
- `start_batch_service` - Bootstrap function to start the service

### 2. Initialize Logging

```python
logging_init()
logger = getLogger("app")
```

This should be called at module level to set up the logging system. Use the returned logger throughout your code for consistent logging.

### 3. Define the Service

Create a `Service` object describing your service:

```python
service = Service(
    name="My Batch Service",
    version=os.environ.get("VERSION", "1.0.0"),
    contact={
        "name": "Your Name",
        "email": "your.email@example.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/license/MIT",
    },
)
```

**Fields:**
- `name` (required) - Human-readable service name
- `version` - Service version (commonly read from `VERSION` environment variable)
- `contact` (required) - Dict with `name` and `email` of service contact
- `license_info` - Dict with `name` and `url` of license

### 4. Define the Request Model

Define a Pydantic model for job input parameters:

```python
class Request(BaseModel):
    jschema: str = Field("urn:sd:schema:my_service.request.1", alias="$schema")
    param1: str = Field(description="First parameter")
    param2: int = Field(default=10, description="Optional second parameter")
    param3: bool | None = Field(False, description="Optional boolean flag")
```

**Requirements:**
- Must inherit from `pydantic.BaseModel`
- Must include a `jschema` field with `alias="$schema"` (IVCAP uses `$schema` for data type identification)
- Every field should have a descriptive `description` for agent clarity
- Use `Field()` to specify defaults and type information
- Use type hints for all fields

**Schema URN Format:** `urn:sd:schema:{service-name}.request.{version}`
- Use a reverse-domain-like format for uniqueness
- Include version number

### 5. Define the Result Model

Define a Pydantic model for job output/results:

```python
class Result(BaseModel):
    jschema: str = Field("urn:sd:schema:my_service.1", alias="$schema")
    result_field: str = Field(description="Main result")
    status: str = Field(description="Job status")
    execution_time: float = Field(description="Time in seconds")
```

**Requirements:**
- Must inherit from `pydantic.BaseModel`
- Must include a `jschema` field with `alias="$schema"`
- All fields should have descriptions
- Should mirror the actual output your worker function produces

**Schema URN Format:** `urn:sd:schema:{service-name}.{version}`
- Similar to request but without `.request` suffix

### 6. Implement the Worker Function

The worker function is the core of your service:

```python
def process_job(req: Request, ctxt: JobContext) -> Result:
    """
    Process a single job.

    This comprehensive description helps agents understand what the service does
    and when to use it. Describe the business logic, inputs, outputs, and any
    side effects.

    Args:
        req: Request object containing job parameters
        ctxt: JobContext with job metadata and reporting facilities

    Returns:
        Result object with computed results
    """
    logger.info(f"Processing job {ctxt.job_id}")

    # Your implementation here
    result = perform_computation(req.param1, req.param2)

    return Result(
        result_field=result,
        status="completed",
        execution_time=elapsed_time,
    )
```

**Function Signature Requirements:**
- First parameter MUST be the Request model type
- Second parameter (optional) MUST be `ctxt: JobContext` if you need job context
- Return type MUST be the Result model type
- All type hints must be present (library uses them for validation)

**Function Behavior:**
- Called once per job by the service
- Must return a Result instance (or raise an exception)
- Has access to job context and reporting facilities

### 7. Using JobContext

The `JobContext` object provides access to job metadata and reporting:

```python
def process_job(req: Request, ctxt: JobContext) -> Result:
    # Access job information
    job_id = ctxt.job_id
    logger.info(f"Processing {job_id}")

    # Create a named execution step with reporting
    with ctxt.report.step("data_preparation", msg="Starting data prep") as step:
        # Do work here
        prepare_data()
        # Update step with completion message
        step.finished(msg="Data preparation complete")

    # Create another step
    with ctxt.report.step("processing", msg="Processing data") as step:
        result = process_data()
        step.finished(msg="Processing complete")

    return Result(result=result)
```

**JobContext Properties:**
- `job_id` - Unique identifier for this job
- `job_authorization` - Authorization token for downstream requests (for IVCAP platform calls)
- `report` - EventReporter for reporting progress and events
- `ivcap` - IVCAP client for platform interactions (lazy-initialized)

**EventReporter Methods:**

The `EventReporter` provides two ways to report events:

1. **Step Context Manager (recommended for progress tracking)**
   - `step(name, msg)` - Create a named step context manager for progress tracking
     - Returns a context manager that yields a step object
     - Call `step.finished(msg)` to mark completion within the context
     - Use for long-running operations to provide progress updates
     - Events are automatically reported when entering/exiting the context

2. **Direct Event Issuance (for immediate notifications)**
   - `step_started(name, msg)` - Report that a step has started
   - `step_info(name, msg)` - Report an informational update for a step
   - `step_error(name, error, context)` - Report an error in a step
   - `step_finished(name, msg)` - Report that a step has finished
   - Use these methods when you need to issue events outside a context manager
   - Useful for conditional reporting or async operations

**Example with direct event issuance:**

```python
def process_job(req: Request, ctxt: JobContext) -> Result:
    report = ctxt.report

    # Start a step directly
    report.step_started("initialization", msg="Starting initialization")

    try:
        result = initialize_system()
        # Report progress updates
        report.step_info("initialization", msg=f"Init progress: {result}%")
    except Exception as e:
        # Report errors directly
        report.step_error("initialization", error=str(e), context="Failed to initialize")
        raise
    finally:
        # Finish the step
        report.step_finished("initialization", msg="Initialization complete")

    return Result(...)
```

This direct approach is particularly useful when:
- Step duration is unknown or highly variable
- Reporting conditional events based on runtime state
- Working with async/await patterns where context managers are awkward
- Needing fine-grained control over event timing

### 8. Interacting with IVCAP Services via context.ivcap

The `JobContext` provides access to an already-instantiated `ivcap` client object, allowing your service to interact with other services, upload/download artifacts, and access platform capabilities without needing explicit authentication credentials.

> **Authentication:** The `ivcap` client is pre-configured with the platform-injected credentials and authorization headers. No JWT token or credentials are required when using `ctxt.ivcap` inside a job container.

**Common Operations:**

#### Discover and invoke other services

```python
def process_job(req: Request, ctxt: JobContext) -> Result:
    """Call another IVCAP service from within this job"""
    ivcap = ctxt.ivcap

    # Find a service by name
    service = ivcap.get_service_by_name("my-downstream-service")

    # Get the service's request model
    ServiceReq = service.request_model

    # Invoke the service and wait for completion
    downstream_job = service.request_job(
        ServiceReq(param1="value", param2=42),
        timeout=300  # wait up to 5 minutes
    )

    # Access the result
    if downstream_job.succeeded:
        result = downstream_job.result
        logger.info(f"Downstream service result: {result}")
    else:
        logger.error(f"Downstream service failed: {downstream_job.status()}")

    return Result(...)
```

This enables **service composition** — your service can orchestrate workflows by chaining calls to other IVCAP services.

#### Upload artifacts

```python
def process_job(req: Request, ctxt: JobContext) -> Result:
    """Generate output and upload as artifacts"""
    ivcap = ctxt.ivcap

    # Generate some output
    output_data = b"result data here"

    # Upload as an artifact
    artifact = ivcap.upload_artifact(
        name="my-result.json",
        io_stream=io.BytesIO(output_data),
        content_type="application/json",
        content_size=len(output_data),
    )

    logger.info(f"Uploaded artifact: {artifact.id}")

    return Result(artifact_urn=artifact.id)
```

Artifacts uploaded by the service are automatically linked to the job in the Datafabric via provenance aspects.

#### Download and read input artifacts

```python
def process_job(req: Request, ctxt: JobContext) -> Result:
    """Download an input artifact and process it"""
    ivcap = ctxt.ivcap

    # Get artifact by URN (passed as a service parameter)
    artifact = ivcap.get_artifact(req.input_artifact_urn)

    # Stream to a local file
    with open("/tmp/input.csv", "wb") as f:
        for chunk in artifact.as_stream():
            f.write(chunk)

    # Or use as a temporary file (auto-deleted)
    with artifact.as_local_file() as path:
        with open(path, "r") as f:
            data = f.read()

    logger.info(f"Processed artifact: {artifact.name} ({artifact.size} bytes)")
    return Result(...)
```

#### Query and attach metadata (Aspects)

```python
def process_job(req: Request, ctxt: JobContext) -> Result:
    """Add domain-specific metadata to artifacts"""
    ivcap = ctxt.ivcap

    # Get an artifact
    artifact = ivcap.get_artifact(req.artifact_urn)

    # List existing metadata/aspects
    for aspect in ivcap.list_aspects(entity=artifact.id):
        logger.info(f"Aspect schema: {aspect.schema}")

    # Attach custom metadata
    annotation = ivcap.add_aspect(
        entity=artifact.id,
        aspect={
            "$schema": "urn:my-service:schema:processing-result.1",
            "processed_by": "my-service",
            "processing_time_seconds": 42.5,
            "status": "success",
            "tags": ["important", "verified"],
        },
    )

    logger.info(f"Added annotation: {annotation.id}")
    return Result(...)
```

Metadata added to artifacts in the Datafabric is queryable and enables rich data discovery and lineage tracking.

#### List services and filter

```python
def process_job(req: Request, ctxt: JobContext) -> Result:
    """Discover available services dynamically"""
    ivcap = ctxt.ivcap

    # List all available services
    for service in ivcap.list_services(limit=50):
        logger.info(f"Service: {service.name} (v{service.version})")

    # Find services by name pattern
    service = ivcap.get_service_by_name("image-processor")

    # Inspect parameters
    for name, param in service.parameters.items():
        print(f"  {name}: {param.type}, optional={param.is_optional}")

    return Result(...)
```

This allows your service to **dynamically discover** what other capabilities are available on the platform.

#### Handle errors gracefully

```python
from ivcap_client.exception import ResourceNotFound, IvcapApiError

def process_job(req: Request, ctxt: JobContext) -> Result:
    """Handle errors when interacting with platform services"""
    ivcap = ctxt.ivcap

    try:
        service = ivcap.get_service_by_name("optional-service")
        job = service.request_job(req, timeout=60)
        result = job.result
    except ResourceNotFound as e:
        logger.warning(f"Service not found: {e.resource}")
        # Gracefully degrade — use fallback logic
        result = fallback_implementation()
    except IvcapApiError as e:
        logger.error(f"Platform API error [{e.status_code}]: {e}")
        raise

    return Result(...)
```

#### Monitor jobs asynchronously

```python
def process_job(req: Request, ctxt: JobContext) -> Result:
    """Submit multiple jobs and monitor them"""
    ivcap = ctxt.ivcap

    # Dispatch multiple downstream jobs
    service = ivcap.get_service_by_name("batch-processor")
    jobs = []
    for item in req.items:
        Model = service.request_model
        job = service.request_job(Model(data=item), timeout=0)  # don't wait
        jobs.append(job)

    logger.info(f"Dispatched {len(jobs)} jobs")

    # Monitor them
    completed = []
    while len(completed) < len(jobs):
        for job in jobs:
            if job not in completed:
                job.refresh()
                if job.finished:
                    logger.info(f"Job {job.id} finished with status {job.status()}")
                    completed.append(job)
        time.sleep(5)

    return Result(job_count=len(jobs), all_succeeded=all(j.succeeded for j in jobs))
```

**Key Benefits of Using context.ivcap:**

1. **No credential management** - Already authenticated with platform context
2. **Service composition** - Chain services together for complex workflows
3. **Data lineage** - Artifacts and metadata are automatically linked via provenance
4. **Dynamic discovery** - Find and use available services at runtime
5. **Rich metadata** - Attach domain-specific aspects to any entity
6. **Error handling** - Graceful degradation when platform operations fail

**Common Patterns:**

| Pattern | Use Case |
|---------|----------|
| **Service chaining** | Invoke sequential analysis steps |
| **Map-reduce** | Dispatch parallel jobs, aggregate results |
| **Conditional branching** | Route to different services based on data |
| **Fallback logic** | Try primary service, use alternative if unavailable |
| **Result aggregation** | Combine outputs from multiple jobs |
| **Metadata enrichment** | Add classifications, tags, provenance info |

For more details on IVCAP client capabilities, refer to the [ivcap-client SDK documentation](../ivcap-client-sdk-python/SKILLS.md).

### 9. Error Handling

Exceptions in the worker function are caught and converted to `ExecutionError`:

```python
def process_job(req: Request, ctxt: JobContext) -> Result:
    if req.param1 < 0:
        raise ValueError("param1 must be positive")

    if req.param2 > 100:
        raise ValueError("param2 cannot exceed 100")

    return Result(result="success")
```

**Error Handling Behavior:**
- Unhandled exceptions are automatically converted to `ExecutionError`
- The error type, message, and traceback are preserved
- The job is marked as failed on the platform
- The service continues processing the next job

### 10. Logging

Use the logger throughout your code:

```python
logger.debug("Detailed debug information")
logger.info("Important milestones")
logger.warning("Unexpected but recoverable issues")
logger.error("Serious errors (but doesn't stop the service)")
```

**Logging Best Practices:**
- Initialize with `logging_init()` at module level
- Use `getLogger("component_name")` for module-specific loggers
- Log important state transitions and milestones
- Include context (job_id, etc.) in log messages
- Use appropriate log levels

### 11. Start the Service

At the bottom of your service file:

```python
if __name__ == "__main__":
    start_batch_service(service, process_job)
```

**Function Signature:**
```python
start_batch_service(
    service_description: Service,
    worker_fn: Callable[..., Any],
    *,
    custom_args: Callable[[argparse.ArgumentParser], argparse.Namespace] | None = None,
    run_opts: dict[str, Any] | None = None,
    with_telemetry: bool | None = None,
)
```

**Parameters:**
- `service_description` - The Service object created earlier
- `worker_fn` - The worker function to call for each job
- `custom_args` (optional) - Function to add custom command-line arguments
- `run_opts` (optional) - Additional runtime options
- `with_telemetry` (optional) - Enable OpenTelemetry instrumentation

**Command-Line Options (automatic):**
- `--print-service-description` - Print service metadata
- `--print-tool-description` - Print tool schema
- `--test-file <path>` - Test service with a job file (useful for debugging)
- `--with-telemetry` - Enable OpenTelemetry tracing

### 12. Testing

Test your service locally using a job file:

```json
{
  "id": "urn:ivcap:job:test-123",
  "in-content-type": "application/json",
  "in-content": {
    "param1": "value1",
    "param2": 42
  }
}
```

Run with test file:
```bash
python my_service.py --test-file job.json
```

This executes your worker function once with the provided input and prints the result.

### 13. Service Definition and Metadata

To view generated service metadata:

```bash
python my_service.py --print-service-description
python my_service.py --print-tool-description
```

These print JSON schemas and metadata that IVCAP uses to:
- Understand service capabilities
- Display in UI
- Route jobs appropriately
- Help agents understand when to use the service

## Advanced Features

### Environment Variables

Common environment variables used by the SDK:

- `VERSION` - Service version (used if not provided to Service constructor)
- `IVCAP_BASE_URL` - IVCAP platform URL (for job fetching and result reporting)
- `OPENOBSERVE_URL` - OpenObserve endpoint for log/metric export
- `OPENOBSERVE_ORG` - OpenObserve organization
- `OPENOBSERVE_USERNAME` - OpenObserve username
- `OPENOBSERVE_TOKEN` - OpenObserve authentication token
- `OTEL_EXPORTER_OTLP_ENDPOINT` - OpenTelemetry endpoint

### Logging to OpenObserve

The SDK automatically exports logs and metrics to OpenObserve when configured:

```bash
export OPENOBSERVE_URL="https://observe.example.com"
export OPENOBSERVE_ORG="myorg"
export OPENOBSERVE_USERNAME="user@example.com"
export OPENOBSERVE_TOKEN="token"
```

All logs via `getLogger()` are automatically sent to OpenObserve.

### OpenTelemetry Support

For distributed tracing, enable with:

```bash
python my_service.py --with-telemetry
```

And configure the OTEL endpoint:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://otel-collector:4318"
```

The SDK automatically:
- Creates spans for each job execution
- Records job outcomes (success/error)
- Instruments HTTP requests/responses
- Records execution duration and errors

### Custom Arguments

Add custom command-line arguments:

```python
def add_custom_args(parser):
    parser.add_argument('--custom-option', type=str, help='Custom option')
    return parser.parse_args()

if __name__ == "__main__":
    start_batch_service(
        service,
        process_job,
        custom_args=add_custom_args,
    )
```

## Project Structure

A typical IVCAP batch service project layout:

```
my_service/
├── pyproject.toml           # Poetry configuration
├── poetry.lock              # Dependencies lock file
├── Dockerfile               # Docker image for deployment
├── my_service.py            # Main service code
├── tests/
│   ├── job1.json           # Test job files
│   └── job2.json
├── requirements.txt         # Optional pip requirements
└── README.md               # Service documentation
```

### pyproject.toml Configuration

Key sections for IVCAP services:

```toml
[project]
name = "my-service"
version = "1.0.0"
description = "My batch service"

[project.dependencies]
python = ">=3.10,<4.0"
pydantic = ">=2.0"
ivcap_service = "^0.6.3"

[tool.poetry-plugin-ivcap]
service-file = "my_service.py"
service-id = "urn:ivcap:service:unique-uuid"
service-type = "batch"
```

## Docker Deployment

Example Dockerfile:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy service code
COPY my_service.py .
COPY pyproject.toml .
COPY poetry.lock .

# Install dependencies
RUN pip install poetry && poetry install --no-dev

ENV VERSION="1.0.0"
ENV IVCAP_BASE_URL="http://ivcap.local"

CMD ["python", "my_service.py"]
```

Build and run:

```bash
docker build -t my-service .
docker run -e IVCAP_BASE_URL="http://ivcap.local" my-service
```

## Complete Example Breakdown

The `examples/test-batch/batch_service.py` demonstrates:

1. **Service Definition** - Describes a CPU load testing service
2. **Request Model** - Parameters for duration, CPU %, and error injection
3. **Result Model** - Returns execution time and status
4. **Worker Function** - `consume_compute()` performs the actual work
5. **Error Handling** - Gracefully handles exceptions, exit codes, OOM
6. **Progress Reporting** - Uses `ctxt.report.step()` to track execution
7. **Logging** - Logs important milestones and debug info
8. **Bootstrap** - Uses `start_batch_service()` to run

Key patterns used:

- **Step-based progress**: Wraps work in named steps for tracking
- **Comprehensive docstrings**: Explains what the service does
- **Flexible error modes**: Tests exception handling, exit codes, OOM errors
- **Resource configuration**: Demonstrates parameter ranges and types

## Best Practices

### 1. Request and Result Models

- **Use descriptive field names** - Make it clear what each field represents
- **Provide comprehensive descriptions** - Agents use these to understand inputs/outputs
- **Use appropriate types** - `int`, `str`, `bool`, `list`, `dict`, etc.
- **Set sensible defaults** - Use `Field(default=...)` for optional parameters
- **Validate data** - Use Pydantic validators for complex constraints

### 2. Worker Function

- **Keep it focused** - Process one job at a time
- **Use meaningful names** - `process_job`, `analyze_data`, `generate_report`
- **Add comprehensive docstring** - Explain what the service does and when to use it
- **Log key milestones** - Help users and developers understand execution
- **Use steps for progress** - Wrap long operations in `ctxt.report.step()`
- **Handle errors gracefully** - Raise informative exceptions

### 3. Deployment

- **Version your service** - Use semantic versioning
- **Containerize properly** - Use Docker for reproducible deployments
- **Configure environment variables** - Document all required and optional env vars
- **Test before deploying** - Use `--test-file` to verify locally
- **Monitor execution** - Enable logging and OpenObserve for observability

### 4. Documentation

- **Write detailed service descriptions** - Explain business logic and use cases
- **Document all parameters** - In model field descriptions
- **Provide example inputs** - Include sample request JSON files
- **List dependencies** - In pyproject.toml and documentation
- **Document deployment requirements** - Resource limits, environment variables

## Troubleshooting

### Service won't start

- Check `IVCAP_BASE_URL` environment variable
- Ensure IVCAP platform is accessible
- Check logs for connection errors

### Jobs not being processed

- Verify service is running: `docker logs <container>`
- Check IVCAP platform job queue
- Ensure service description is registered

### Incorrect results

- Run with `--test-file` to debug locally
- Check Request model matches actual data
- Verify Result model serialization

### Memory or performance issues

- Profile worker function
- Check for unbounded loops or memory leaks
- Monitor logs and metrics via OpenObserve

## Related Documentation

- [IVCAP Platform Documentation](https://ivcap.works)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Python asyncio (for async services)](https://docs.python.org/3/library/asyncio.html)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
