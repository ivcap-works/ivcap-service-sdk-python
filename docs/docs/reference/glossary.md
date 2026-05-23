# Glossary

Key terms and concepts used in the IVCAP Service SDK.

## Artifact

A file or data object stored in the IVCAP platform. Services download artifacts as input and upload artifacts as results.

## Batch Service

A service that processes discrete jobs asynchronously. Each job is independent and runs to completion.

## JobContext

The context object passed to your job processor function. Provides access to job metadata, progress reporting, and platform APIs.

## Service

A reusable, containerized application registered with IVCAP that processes jobs. Defined by a `Service` class with metadata.

## Service Composition

Building complex workflows by composing multiple services together. One service calls another service during job processing.

## Collection

A logical grouping of artifacts in the IVCAP platform. Used for organizing related results.

## Event

A message sent during job execution to report progress, errors, or other status information.

## Step

A named phase of job processing. Steps are used to track progress and report metrics.

## Progress Reporting

The mechanism for services to communicate job status, progress, and metrics back to IVCAP. Implemented via the event system.

## Request/Result Models

Pydantic models that define the input (Request) and output (Result) schemas for your service.

## OpenObserve

An observability platform used for log aggregation, metrics collection, and tracing.

## OpenTelemetry

An open standard for exporting logs, metrics, and traces from applications.

## OTLP

OpenTelemetry Protocol - the protocol used to export telemetry data to OpenObserve and other collectors.

## Schema

A JSON Schema definition for the Request or Result model. Describes the structure of data that flows through your service.

## URN

Uniform Resource Name. IVCAP uses URNs to identify resources (services, artifacts, etc.). Format: `urn:ivcap:service:service-id`

## See Also

- [API Reference](../api/overview.md)
- [Getting Started](../getting-started/quick-start.md)
