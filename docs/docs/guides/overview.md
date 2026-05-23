# Guides Overview

These guides provide deep dives into specific features and patterns for building IVCAP services.

## Getting Started

If you're new to the SDK, start here:

1. **[Installation](../getting-started/installation.md)** — Set up the SDK
2. **[Quick Start](../getting-started/quick-start.md)** — 5-minute introduction
3. **[Your First Service](../getting-started/first-service.md)** — Build a real service

## Core Concepts

### [Job Processing](job-processing.md)

Learn how to define and process jobs:
- Request/Result schemas with Pydantic
- Accessing job context
- Progress tracking and reporting
- Common patterns

**Read this if:** You want to understand the fundamentals of building service handlers.

### [Working with Artifacts](artifacts.md)

Upload and download files:
- Downloading input artifacts
- Uploading results
- Handling file streams
- Working with collections

**Read this if:** Your service processes or generates files.

### [Service Composition](service-composition.md)

Call other IVCAP services:
- Service discovery
- Dynamic invocation
- Parameter passing
- Handling results

**Read this if:** You need to compose multiple services together.

## Advanced Topics

### [Observability & Logging](observability.md)

Monitor your services:
- Structured logging
- OpenObserve integration
- Progress events
- OpenTelemetry tracing

**Read this if:** You want comprehensive monitoring and debugging.

### [Error Handling](error-handling.md)

Build robust services:
- Exception handling patterns
- Reporting errors
- Retry strategies
- Graceful degradation

**Read this if:** You need production-grade error handling.

### [Deployment](deployment.md)

Deploy to production:
- Docker containerization
- Environment configuration
- Service registration
- Scalability patterns

**Read this if:** You're ready to deploy your service.

### [Best Practices](best-practices.md)

Pro tips and patterns:
- Code organization
- Testing strategies
- Performance optimization
- Common pitfalls

**Read this if:** You want to write production-quality code.

## Learning Path

```
Installation
    ↓
Quick Start
    ↓
Your First Service
    ↓
Job Processing
    ├→ Artifacts (if needed)
    ├→ Service Composition (if needed)
    └→ Observability (if needed)
    ↓
Error Handling
    ↓
Deployment
    ↓
Best Practices
```

## Choose Your Own Path

- **I want to process data:** [Job Processing](job-processing.md) → [Error Handling](error-handling.md)
- **I need to work with files:** [Artifacts](artifacts.md)
- **I need to call other services:** [Service Composition](service-composition.md)
- **I want to monitor my service:** [Observability](observability.md)
- **I'm ready for production:** [Deployment](deployment.md) → [Best Practices](best-practices.md)

## See Also

- **[API Reference](../api/overview.md)** — Complete API documentation
- **[Examples](../examples/batch-service.md)** — Working code samples
- **[Reference](../reference/environment-variables.md)** — Configuration and schemas
