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

## OpenObserve Integration

### OPENOBSERVE_URL
- **Type**: String
- **Description**: Base URL for OpenObserve instance
- **Example**: `https://observe.example.com`

### OPENOBSERVE_ORG
- **Type**: String
- **Description**: OpenObserve organization name
- **Example**: `production`

### OPENOBSERVE_USERNAME
- **Type**: String
- **Description**: OpenObserve username for authentication
- **Example**: `service@example.com`

### OPENOBSERVE_TOKEN
- **Type**: String
- **Description**: OpenObserve API token
- **Example**: `zo_prod_...`

### OPENOBSERVE_ENABLE_LOGS
- **Type**: Boolean
- **Default**: `true`
- **Description**: Enable log export to OpenObserve
- **Values**: `true`, `false`, `1`, `0`

### OPENOBSERVE_ENABLE_METRICS
- **Type**: Boolean
- **Default**: `true`
- **Description**: Enable metrics export to OpenObserve
- **Values**: `true`, `false`, `1`, `0`

### OPENOBSERVE_METRICS_INTERVAL
- **Type**: Integer
- **Default**: `60`
- **Description**: Metrics collection interval in seconds
- **Example**: `30`

## OpenTelemetry Configuration

### OTEL_EXPORTER_OTLP_ENDPOINT
- **Type**: String
- **Description**: Custom OTLP endpoint for metrics and traces
- **Example**: `http://otel-collector:4318`

### OTEL_EXPORTER_OTLP_HEADERS
- **Type**: String
- **Description**: Custom headers for OTLP exports
- **Example**: `Authorization=Bearer <token>,x-scope=service`

### OPENOBSERVE_USE_UNIFIED_OTLP_ENDPOINT
- **Type**: Boolean
- **Default**: `false`
- **Description**: Use OpenObserve unified OTLP endpoint
- **Values**: `true`, `false`

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
ENV OPENOBSERVE_URL="https://observe.example.com"
ENV OPENOBSERVE_ORG="production"
```

### Docker Compose

```yaml
services:
  my-service:
    environment:
      OPENOBSERVE_URL: https://observe.example.com
      OPENOBSERVE_ORG: production
```

### Kubernetes

```yaml
containers:
- name: my-service
  env:
  - name: OPENOBSERVE_URL
    value: "https://observe.example.com"
  - name: OPENOBSERVE_TOKEN
    valueFrom:
      secretKeyRef:
        name: observability
        key: token
```

### Command Line

```bash
export OPENOBSERVE_URL="https://observe.example.com"
export OPENOBSERVE_ORG="production"
python my_service.py
```

## See Also

- [Observability Guide](../guides/observability.md)
- [Deployment Guide](../guides/deployment.md)
