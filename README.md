# ivcap-service: Python SDK for Building IVCAP Batch Services

<a href="https://scan.coverity.com/projects/ivcap-service-sdk-python">
  <img alt="Coverity Scan Build Status"
       src="https://scan.coverity.com/projects/31773/badge.svg"/>
</a>

**A Python library for building batch services on the IVCAP platform.**

This SDK simplifies development of long-running, queue-based worker services that integrate with the IVCAP data and compute platform: typed Pydantic request/result models, automatic error handling, artifact upload/download, service composition, progress reporting, and export of logs/metrics/traces to observability platforms.

📖 **Full documentation: [ivcap-works.github.io/ivcap-service-sdk-python](https://ivcap-works.github.io/ivcap-service-sdk-python/)**
🤖 **Agent/LLM quick-reference: [`AGENTS.md`](./AGENTS.md)**

## Table of Contents

- [Quick Start](#quick-start)
- [Examples](#examples)
- [Template Repository](#template-repository)
- [Maintenance \& Development Guide](#maintenance--development-guide)
- [Contributing](#contributing)
- [License](#license)

## Quick Start

```bash
pip install ivcap_service
```

```python
from pydantic import BaseModel, Field
from ivcap_service import (
    Service, ServiceContact, ServiceLicense,
    JobContext, start_batch_service, getLogger, logging_init, with_schema,
)

logging_init()
logger = getLogger("app")

service = Service(
    name="My Batch Service",
    contact=ServiceContact(name="Your Name", email="you@example.com"),
    license=ServiceLicense(name="MIT", url="https://opensource.org/license/MIT"),
)

@with_schema("urn:sd:schema:my_service.request.1")
class Request(BaseModel):
    input_data: str = Field(description="The data to process")

@with_schema("urn:sd:schema:my_service.1")
class Result(BaseModel):
    output_data: str = Field(description="The processed result")

def process_job(req: Request, ctxt: JobContext) -> Result:
    """
    Process a job.

    This comprehensive description helps others understand what your service does.
    """
    with ctxt.report.step("processing", message="Starting work") as step:
        result = req.input_data.upper()  # Your logic here
        step.finished(message="Processing complete")

    return Result(output_data=result)

if __name__ == "__main__":
    start_batch_service(service, process_job)
```

```bash
# Test locally (job must be wrapped in the id/in-content-type/in-content envelope,
# see the Quick Start guide linked below)
python my_service.py --test-file test_job.json

# Print service metadata
python my_service.py --print-service-description

# Run the service (will wait for jobs)
python my_service.py
```

For everything else — `JobContext`, artifact management, service composition,
error handling, observability/OpenTelemetry/OpenObserve, deployment, and best
practices — see the full documentation:

- **[Quick Start](https://ivcap-works.github.io/ivcap-service-sdk-python/getting-started/quick-start/)** and **[Your First Service](https://ivcap-works.github.io/ivcap-service-sdk-python/getting-started/first-service/)**
- **[Guides](https://ivcap-works.github.io/ivcap-service-sdk-python/guides/overview/)** — job processing, artifacts, service composition, observability, error handling, deployment, best practices
- **[API Reference](https://ivcap-works.github.io/ivcap-service-sdk-python/api/overview/)**
- **[Environment Variables Reference](https://ivcap-works.github.io/ivcap-service-sdk-python/reference/environment-variables/)**
- **[`AGENTS.md`](./AGENTS.md)** — a single, comprehensive, machine-readable reference for AI coding assistants

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

## Template Repository

Get started quickly with the community template:

```bash
git clone https://github.com/ivcap-works/ivcap-python-ai-tool-template.git
cd ivcap-python-ai-tool-template
# Follow the template's README
```

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
