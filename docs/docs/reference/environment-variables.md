# Environment Variables Reference

Complete reference of all environment variables used by the IVCAP Service SDK.

## Service Configuration

### IVCAP_BASE_URL
- **Type**: String
- **Default**: unset - the service will still run locally, but sidecar
  communication (fetching jobs, pushing results/events) is disabled; use
  `--test-file` for local testing in that case
- **Description**: Base URL of the IVCAP sidecar this service instance talks
  to for fetching jobs and pushing results/events. Set automatically by the
  IVCAP runtime when the service runs as a deployed batch container
- **Example**: `http://ivcap.local`

### IVCAP_SERVICE_ID
- **Type**: String
- **Description**: This service's IVCAP URN. Used as the `$id` in the
  generated service definition (`--print-service-description`). Also used for
  OpenTelemetry tagging - see [below](#ivcap_service_id)
- **Example**: `urn:ivcap:service:3678e5f1-8fb7-5ad6-b65b-8bd8c23c0948`

### IVCAP_SERVICE_NAME
- **Type**: String
- **Default**: the `name` passed to the `Service(...)` constructor
- **Description**: Overrides the service name used in the generated service
  definition
- **Example**: `my-batch-service`

### IVCAP_POLICY_URN
- **Type**: String
- **Default**: `urn:ivcap:policy:ivcap.open.service`
- **Description**: Access policy URN included in the generated service
  definition

### IVCAP_RESOURCES_FILE
- **Type**: String
- **Default**: `resources.json`
- **Description**: Path to a JSON file describing CPU/memory resource
  requests and limits, included in the generated service definition. See
  [Service Definition Schema](service-definition.md)

### DOCKER_IMG
- **Type**: String
- **Description**: Docker image reference included as the controller `image`
  in the generated service definition (`--print-service-description`).
  Typically set by the CI/build pipeline, not by service authors

### ENTRYPOINT / DOCKERFILE
- **Type**: String
- **Description**: Used by `--print-service-description` to determine the
  container entrypoint command. `ENTRYPOINT` (a Python list literal, e.g.
  `["python", "my_service.py"]`) takes precedence; otherwise the SDK parses
  the `ENTRYPOINT` line out of the file named by `DOCKERFILE` (default
  `Dockerfile`)

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

### Command-line flags: `--with-telemetry` / `--without-telemetry`

OpenTelemetry auto-instrumentation of outbound `requests`/`httpx` calls is
**auto-enabled** whenever `OTEL_EXPORTER_OTLP_ENDPOINT` is configured - no
flag is needed in the common case. These mutually-exclusive flags override
that default:

- `--with-telemetry` - force-enable instrumentation, even if no endpoint is
  configured yet (logs a warning in that case).
- `--without-telemetry` - force-disable instrumentation, even if an
  endpoint is configured. Log/metric export via OpenObserve is unaffected.

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

## Networking / Proxying

The SDK can patch outbound `requests`/`httpx` calls made from inside your
worker function to propagate job context and, optionally, route external
calls through a proxy. This is installed automatically by the runtime (via
`ivcap_service.context.set_context(...)`) for both `requests.Session.send`
and `httpx.Client.send`/`AsyncClient.send`.

For every outbound request, the SDK first classifies the destination
hostname as **local** or **external**:

- **Local** - hostname ends with `.local`, `.minikube`, or `.ivcap.net`
  (i.e. it targets the IVCAP platform/sidecar or other in-cluster
  services). Local requests get an `Authorization: <job_authorization>`
  header added automatically (using the job's own authorization token), and
  are **not** routed through `IVCAP_PROXY_URL`. (OTEL collector endpoints -
  URLs matching `OTEL_EXPORTER_OTLP_ENDPOINT` - are exempt from the
  `Authorization` header even if otherwise local.)
- **External** - any other hostname (e.g. a third-party API). External
  requests do **not** get an `Authorization` header, but are rerouted
  through `IVCAP_PROXY_URL` if it is set (see below).

In both cases, an `Ivcap-Job-Id: <job_id>` header is added so downstream
services/proxies can correlate the call with the originating job.

### IVCAP_PROXY_URL
- **Type**: String
- **Default**: unset - external calls are left untouched (no rerouting)
- **Description**: When set, every outbound request to an **external**
  (non-local) hostname is rewritten to target this URL instead of its
  original destination. The original, full destination URL (including query
  parameters) is preserved in the `Ivcap-Forward-Url` request header, so
  whatever is listening at `IVCAP_PROXY_URL` is expected to read that header
  and forward the request on to the real destination (e.g. for egress
  auditing, access control, or network isolation of the job sandbox). This
  is typically set by the IVCAP runtime/container environment rather than
  by service authors; for local testing you can point it at a local proxy
  process.
- **Example**: `http://127.0.0.1:8888`

**Example outbound request to `https://example.com/api?x=1`, with
`IVCAP_PROXY_URL=http://127.0.0.1:8888`:**

```
GET http://127.0.0.1:8888
Ivcap-Forward-Url: https://example.com/api?x=1
Ivcap-Job-Id: urn:ivcap:job:51d29d96-fa70-4125-84ba-4628fda220c3
```

> **Troubleshooting**: if the proxy at `IVCAP_PROXY_URL` responds with
> `431 Request Header Fields Too Large`, check that it can handle the
> `Ivcap-Forward-Url` header (which may contain a long URL with query
> parameters) and that it implements the expected forward-by-header
> protocol - a generic HTTP forward/CONNECT proxy is **not** a drop-in
> replacement.

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
