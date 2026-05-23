# ivcap-service: Python SDK for Building IVCAP Batch Services

<a href="https://scan.coverity.com/projects/ivcap-service-sdk-python">
  <img alt="Coverity Scan Build Status"
       src="https://scan.coverity.com/projects/31773/badge.svg"/>
</a>

**A Python library for building batch services on the IVCAP platform.**

This SDK simplifies development of long-running, queue-based worker services that integrate with the IVCAP data and compute platform. With minimal boilerplate, you can build services that:

- Process jobs asynchronously with automatic error handling
- Upload, download, and process artifacts
- Compose with other IVCAP services dynamically
- Report progress and metadata throughout execution
- Export logs and metrics to observability platforms

## Table of Contents

- [Quick Start](#quick-start)
  - [1. Define Your Service](#1-define-your-service)
  - [2. Run It](#2-run-it)
- [Core Features](#core-features)
  - [Job Processing](#job-processing)
  - [IVCAP Platform Integration](#ivcap-platform-integration)
  - [Observability](#observability)
- [Examples](#examples)
- [Comprehensive Documentation](#comprehensive-documentation)
- [OpenObserve Integration (Logs + Metrics)](#openobserve-integration-logs--metrics)
  - [Basic Setup](#basic-setup)
  - [Advanced Configuration](#advanced-configuration)
- [Template Repository](#template-repository)
- [What This Library Provides](#what-this-library-provides)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

## Quick Start

### 1. Define Your Service

```python
from pydantic import BaseModel, Field
from ivcap_service import Service, JobContext, start_batch_service, getLogger, logging_init

logging_init()
logger = getLogger("app")

service = Service(
    name="My Batch Service",
    contact={"name": "Your Name", "email": "you@example.com"},
    license_info={"name": "MIT", "url": "https://opensource.org/license/MIT"},
)

class Request(BaseModel):
    jschema: str = Field("urn:sd:schema:my_service.request.1", alias="$schema")
    input_data: str = Field(description="The data to process")

class Result(BaseModel):
    jschema: str = Field("urn:sd:schema:my_service.1", alias="$schema")
    output_data: str = Field(description="The processed result")

def process_job(req: Request, ctxt: JobContext) -> Result:
    """
    Process a job.

    This comprehensive description helps others understand what your service does.
    """
    with ctxt.report.step("processing", msg="Starting work") as step:
        result = req.input_data.upper()  # Your logic here
        step.finished(msg="Processing complete")

    return Result(output_data=result)

if __name__ == "__main__":
    start_batch_service(service, process_job)
```

### 2. Run It

```bash
# Test locally
python my_service.py --test-file test_job.json

# Print service metadata
python my_service.py --print-service-description

# Run the service (will wait for jobs)
python my_service.py
```

## Core Features

### Job Processing
- **Request/Result Models**: Use Pydantic to define typed inputs and outputs
- **JobContext**: Access job metadata, progress reporting, and platform APIs
- **Error Handling**: Automatic exception capture and reporting
- **Progress Tracking**: Report work progress with named steps

### IVCAP Platform Integration
- **Service Composition**: Call other services from within your job
- **Artifact Management**: Upload and download files
- **Metadata**: Attach domain-specific metadata (aspects) to artifacts
- **Service Discovery**: Dynamically find and invoke available services

### Observability
- **Logging**: Structured logging with automatic export to OpenObserve
- **Progress Events**: Track job steps with automatic timestamps and reporting
- **OpenTelemetry**: Distributed tracing support for workflow monitoring
- **Metrics**: Automatic job count and duration metrics

## Examples

This repository includes example services:

- **`examples/test-batch/`** - A complete batch service example with CPU load testing, error handling, and progress reporting. Start here to understand the patterns.
- **`examples/test-api/`** - Example service showing artifact interaction patterns.

Run the examples to see how they work:

```bash
cd examples/test-batch
python batch_service.py --print-service-description
python batch_service.py --test-file tests/req_1.json
```

## Comprehensive Documentation

**This README provides a quick overview. For in-depth guidance, see [`SKILLS.md`](./SKILLS.md)**, which covers:

- **Step-by-step guide** to building batch services
- **JobContext API** - progress reporting, artifact upload/download, service composition
- **Error handling** - exception patterns and recovery
- **Advanced features** - environment variables, OpenTelemetry, custom arguments
- **Deployment** - Docker configuration, production patterns
- **Best practices** - code organization, documentation, testing
- **Troubleshooting** - common issues and solutions

**`SKILLS.md` is designed for:**
- Developers wanting deep technical understanding
- Agents/LLMs needing detailed implementation guidance
- Anyone building complex, multi-service workflows

## OpenObserve Integration (Logs + Metrics)

This SDK can export logs and metrics to **OpenObserve** via OpenTelemetry. It's **opt-in** and configured via environment variables.

### Basic Setup

```bash
export OPENOBSERVE_URL="https://observe.example.com"
export OPENOBSERVE_ORG="myorg"
export OPENOBSERVE_USERNAME="service@example.com"
export OPENOBSERVE_TOKEN="<service-token>"
```

When configured, the SDK automatically exports:
- **Python logging** records
- **Runtime metrics**:
  - `ivcap.jobs_total` - Total jobs processed
  - `ivcap.job_duration_seconds` - Job execution duration histogram

### Advanced Configuration

```bash
# Use explicit OTLP endpoint
export OTEL_EXPORTER_OTLP_ENDPOINT="http://otel-collector:4318"

# Or use OpenObserve unified OTLP endpoint
export OPENOBSERVE_USE_UNIFIED_OTLP_ENDPOINT=true

# Custom headers
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer <token>,x-scope=service"

# Control signals and streams
export OPENOBSERVE_ENABLE_LOGS=true
export OPENOBSERVE_ENABLE_METRICS=true
export OPENOBSERVE_METRICS_INTERVAL=30
```

See [`SKILLS.md`](./SKILLS.md) for more configuration options.

## Template Repository

Get started quickly with the community template:

```bash
git clone https://github.com/ivcap-works/ivcap-python-ai-tool-template.git
cd ivcap-python-ai-tool-template
# Follow the template's README
```

## What This Library Provides

| Component | Purpose |
|-----------|---------|
| `Service` | Describe your service metadata |
| `JobContext` | Access job info, reporting, and IVCAP APIs |
| `start_batch_service()` | Bootstrap the service runner |
| `getLogger()` / `logging_init()` | Structured logging with OpenObserve export |
| `ivcap` client (via context) | Interact with IVCAP platform |

## Project Structure

A typical IVCAP service project:

```
my-service/
├── my_service.py          # Main service code
├── pyproject.toml         # Python dependencies
├── Dockerfile             # Container image
├── tests/
│   ├── request1.json      # Test job files
│   └── request2.json
└── README.md              # Service documentation
```

See `examples/test-batch/` for a complete working example.

## Maintenance & Development Guide

This section is for maintainers and developers working on the SDK itself.

### Setup Development Environment

```bash
# Install the SDK and all development dependencies
make setup

# Or manually with Poetry
poetry config virtualenvs.in-project true --local
poetry install
```

### Testing

Run the test suite:

```bash
# Run all tests with coverage
make test

# Or with Poetry directly
poetry run pytest tests/ --cov=ivcap_service --cov-report=xml
```

### Code Quality

Maintain code quality standards:

```bash
# Run linting checks
make lint

# Run type checking
make typecheck

# Format code
make fmt

# Or run all checks together
make check    # Runs: lint + typecheck + test
```

### Building

Build distribution packages:

```bash
# Build wheel and source distribution
make build

# Publish to PyPI (requires credentials configured in Poetry)
make publish
```

### Documentation

The SDK includes comprehensive documentation built with MkDocs:

```bash
# Serve documentation locally (http://localhost:8000)
make docs-serve

# Build documentation static site
make docs

# Clean generated documentation
make docs-clean
```

**Documentation Structure:**
- `docs/docs/` - Source Markdown files organized by topic
- `docs/mkdocs.yml` - MkDocs configuration
- `docs/site/` - Generated HTML (created when building)

**Documentation includes:**
- Getting Started guides
- Comprehensive feature guides
- API reference
- Working examples
- Best practices and patterns
- Environment variable reference

See `docs/docs/community/contributing.md` for documentation contribution guidelines.

### Common Maintenance Tasks

**Make targets for quick access:**

```bash
make setup           # Initial setup
make check           # Validate code (lint + typecheck + test)
make fmt             # Format code
make docs-serve      # Preview documentation
make clean           # Remove build artifacts
```

**Poetry tasks (via poethepoet):**

```bash
poetry run poe lint        # Run ruff linting
poetry run poe format      # Run ruff formatting
poetry run poe typecheck   # Run pyright type checking
poetry run poe docs        # Build documentation
poetry run poe docs-serve  # Serve documentation
poetry run poe docs-clean  # Clean documentation
```

### Release Process

1. Update version in `pyproject.toml`
2. Run `make check` to verify all tests pass
3. Build: `make build`
4. Publish: `make publish` (requires PyPI credentials)
5. Update documentation if needed: `make docs`

## Contributing

We welcome contributions! Please check [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

## License

See [LICENSE](./LICENSE) and [CONDUCT.md](./CONDUCT.md) for details.
