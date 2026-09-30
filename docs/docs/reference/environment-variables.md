# Environment Variables Reference

Complete reference of all environment variables used by the IVCAP Service SDK.

## Service Configuration

### IVCAP_URL
- **Type**: String
- **Default**: Auto-detected from environment
- **Description**: Base URL for the IVCAP platform
- **Example**: `https://ivcap.example.com`

### IVCAP_API_KEY
- **Type**: String
- **Description**: API key for IVCAP authentication
- **Example**: `sk_prod_...`

## OpenTelemetry / OpenObserve Configuration

Telemetry export (logs, metrics, traces via OTLP/HTTP) is enabled implicitly
as soon as a usable OTLP endpoint can be resolved - from *either* a plain,
standard `OTEL_EXPORTER_OTLP_ENDPOINT` *or* OpenObserve-specific config
(`OPENOBSERVE_URL` / `OPENOBSERVE_OTLP_ENDPOINT`). **A plain OTEL endpoint is
sufficient on its own; none of the `OPENOBSERVE_*` variables below are
required just to turn export on.** They are all optional and only ever *add*
extra information on top (auth, stream-name routing, org/URL-derived
endpoint shaping).

### Standard OpenTelemetry variables (sufficient on their own)

### OTEL_EXPORTER_OTLP_ENDPOINT
- **Type**: String
- **Description**: OTLP endpoint for logs, metrics and traces. Setting this
  alone is sufficient to enable telemetry export.
- **Example**: `http://otel-collector:4318`

### OTEL_EXPORTER_OTLP_PROTOCOL
- **Type**: String
- **Description**: OTLP wire protocol. The SDK uses the OTLP/HTTP exporters,
  so this should be `http/protobuf`.
- **Example**: `http/protobuf`

### OTEL_EXPORTER_OTLP_HEADERS
- **Type**: String
- **Description**: Generic custom headers applied to all OTLP exports (comma
  or semicolon separated `k=v` pairs)
- **Example**: `Authorization=Bearer <token>,x-scope=service`

### OTEL_EXPORTER_OTLP_LOGS_HEADERS / OTEL_EXPORTER_OTLP_METRICS_HEADERS / OTEL_EXPORTER_OTLP_TRACES_HEADERS
- **Type**: String
- **Description**: Signal-specific headers; each overrides
  `OTEL_EXPORTER_OTLP_HEADERS` for its respective signal only. Useful for
  OpenObserve's `stream-name` routing header.
- **Example**: `stream-name=default`

### OTEL_SERVICE_NAME
- **Type**: String
- **Description**: Standard OTel resource attribute `service.name`, applied
  to all exported telemetry. Often set automatically by deployment
  platforms/auto-instrumentation wrappers.
- **Example**: `my-batch-service`

### IVCAP_SERVICE_ID
- **Type**: String
- **Description**: This service's IVCAP URN. Tagged as `ivcap.service_id` on
  job/step spans and as a resource attribute on exported telemetry (constant
  across all jobs handled by this service instance).
- **Example**: `urn:ivcap:service:3678e5f1-8fb7-5ad6-b65b-8bd8c23c0948`

### Command-line flag: `--with-telemetry`

Enables OpenTelemetry auto-instrumentation of outbound `requests`/`httpx`
calls, in addition to the OTLP export configured via the env vars above.

### OpenObserve-specific variables (all optional; add extras on top)

### OPENOBSERVE_ENABLED
- **Type**: Boolean
- **Description**: Force enable (`true`, requires a resolvable endpoint - or
  raises an error) or force disable (`false`, even if an endpoint is
  configured) telemetry export. Never required just to enable export when a
  plain OTEL endpoint is present.
- **Values**: `true`, `false`, `1`, `0`

### OPENOBSERVE_URL
- **Type**: String
- **Description**: Base URL for OpenObserve instance (used to derive the
  OTLP endpoint if `OTEL_EXPORTER_OTLP_ENDPOINT` is not set)
- **Example**: `https://observe.example.com`

### OPENOBSERVE_ORG
- **Type**: String
- **Default**: `default`
- **Description**: OpenObserve organization name, combined with
  `OPENOBSERVE_URL` to derive the endpoint (`<url>/api/<org>`)
- **Example**: `production`

### OPENOBSERVE_OTLP_ENDPOINT
- **Type**: String
- **Description**: Full OTLP endpoint URL, overriding the URL derived from
  `OPENOBSERVE_URL`/`OPENOBSERVE_ORG`
- **Example**: `https://observe.example.com/api/production`

### OPENOBSERVE_AUTH
- **Type**: String
- **Description**: Full value for the `Authorization` header (use this for a
  Bearer token)
- **Example**: `Bearer zo_prod_...`

### OPENOBSERVE_USERNAME
- **Type**: String
- **Description**: OpenObserve username for authentication. Must be set
  together with `OPENOBSERVE_TOKEN` (or leave both unset if a proxy injects
  auth)
- **Example**: `service@example.com`

### OPENOBSERVE_TOKEN
- **Type**: String
- **Description**: Convenience: combined with `OPENOBSERVE_USERNAME` into an
  `Authorization: Basic <base64(user:token)>` header
- **Example**: `zo_prod_...`

### OPENOBSERVE_HEADERS
- **Type**: String
- **Description**: OpenObserve-specific headers, merged on top of
  `OTEL_EXPORTER_OTLP_HEADERS`
- **Example**: `x-scope=service`

### OPENOBSERVE_ENABLE_LOGS / OPENOBSERVE_ENABLE_METRICS / OPENOBSERVE_ENABLE_TRACES
- **Type**: Boolean
- **Default**: `true`
- **Description**: Enable/disable export of the respective signal
- **Values**: `true`, `false`, `1`, `0`

### OPENOBSERVE_METRICS_INTERVAL
- **Type**: Integer
- **Default**: `60`
- **Description**: Metrics collection interval in seconds
- **Example**: `30`

### OPENOBSERVE_LOGS_STREAM_NAME / OPENOBSERVE_METRICS_STREAM_NAME / OPENOBSERVE_TRACES_STREAM_NAME
- **Type**: String
- **Default**: `default`
- **Description**: Stream name added via the `stream-name` header (only
  applies when the endpoint originates from OpenObserve-specific config, not
  a plain `OTEL_EXPORTER_OTLP_ENDPOINT` - use the
  `OTEL_EXPORTER_OTLP_*_HEADERS` variables above for that case)

### OPENOBSERVE_ADD_STREAM_NAME_HEADER
- **Type**: Boolean
- **Default**: `true`
- **Description**: Add the `stream-name` header automatically (see above)
- **Values**: `true`, `false`

### OPENOBSERVE_USE_UNIFIED_OTLP_ENDPOINT
- **Type**: Boolean
- **Default**: `false`
- **Description**: Use OpenObserve's unified `/v1/otlp` endpoint for all
  signals instead of signal-specific paths (`/v1/logs`, `/v1/metrics`,
  `/v1/traces`)
- **Values**: `true`, `false`

## Sidecar Communication

### IVCAP_BASE_URL
- **Type**: String
- **Description**: Base URL of the IVCAP sidecar, used for fetching jobs and
  delivering events/results. If unset, the SDK still runs locally but
  sidecar communication is disabled.
- **Example**: `http://ivcap.local`

### Command-line flag: `--test-without-sidecar`

Silently drops any attempt to deliver events or results to the sidecar (no
HTTP calls, no retries, no warnings). Useful for local testing (typically
combined with `--test-file`) without a reachable `IVCAP_BASE_URL`/sidecar.

## Logging Configuration

### IVCAP_LOG_LEVEL
- **Type**: String
- **Default**: `INFO`
- **Description**: Global log level
- **Values**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Example**: `DEBUG`

### IVCAP_LOG_FORMAT
- **Type**: String
- **Description**: Log format specification
- **Example**: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

## Custom Application Variables

You can use any environment variables in your service:

```python
import os

def process_job(req: Request, ctx: JobContext) -> Result:
    api_url = os.getenv("API_URL", "http://localhost:8000")
    api_key = os.getenv("API_KEY")
    timeout = int(os.getenv("API_TIMEOUT", "30"))

    return Result(url=api_url)
```

## Setting Variables

### Docker

```dockerfile
ENV OTEL_EXPORTER_OTLP_ENDPOINT="http://openobserve.example.com/api/production"
ENV OTEL_EXPORTER_OTLP_PROTOCOL="http/protobuf"
```

### Docker Compose

```yaml
services:
  my-service:
    environment:
      OTEL_EXPORTER_OTLP_ENDPOINT: http://openobserve.example.com/api/production
      OTEL_EXPORTER_OTLP_PROTOCOL: http/protobuf
```

### Kubernetes

```yaml
containers:
- name: my-service
  env:
  - name: OTEL_EXPORTER_OTLP_ENDPOINT
    value: "http://openobserve.example.com/api/production"
  - name: OTEL_EXPORTER_OTLP_PROTOCOL
    value: "http/protobuf"
  # Optional: only needed for auth against a secured OpenObserve instance
  - name: OPENOBSERVE_TOKEN
    valueFrom:
      secretKeyRef:
        name: observability
        key: token
```

### Command Line

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://openobserve.example.com/api/production"
export OTEL_EXPORTER_OTLP_PROTOCOL="http/protobuf"
python my_service.py
```

## See Also

- [Observability Guide](../guides/observability.md)
- [Deployment Guide](../guides/deployment.md)
