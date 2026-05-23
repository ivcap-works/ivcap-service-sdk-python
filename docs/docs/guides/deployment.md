# Deployment Guide

Deploy your IVCAP service to production.

## Docker Containerization

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml poetry.lock* ./
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev

# Copy service code
COPY my_service.py .

# Run the service
ENTRYPOINT ["python", "my_service.py"]
```

Build the image:

```bash
docker build -t my-service:latest .
```

## Environment Configuration

### Local Development

```bash
# Optional: OpenObserve integration
export OPENOBSERVE_URL="http://localhost:5080"
export OPENOBSERVE_ORG="myorg"
export OPENOBSERVE_USERNAME="admin@example.com"
export OPENOBSERVE_TOKEN="<token>"

# Run the service
python my_service.py --print-service-description
```

### Production Environment

Set environment variables in your deployment:

```bash
# Service configuration
export IVCAP_URL="https://ivcap.example.com"

# Observability
export OPENOBSERVE_URL="https://observe.example.com"
export OPENOBSERVE_ORG="production"
export OPENOBSERVE_USERNAME="service@example.com"
export OPENOBSERVE_TOKEN="<production-token>"

# Custom settings
export API_KEY="<external-api-key>"
export LOG_LEVEL="INFO"
```

## Service Registration

Get the service definition:

```bash
docker run my-service:latest --print-service-description > service.json
```

Register with IVCAP:

```bash
ivcap service register service.json
```

## Kubernetes Deployment

Create a `deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-service
  template:
    metadata:
      labels:
        app: my-service
    spec:
      containers:
      - name: my-service
        image: my-service:latest
        env:
        - name: OPENOBSERVE_URL
          value: "https://observe.example.com"
        - name: OPENOBSERVE_ORG
          valueFrom:
            secretKeyRef:
              name: observability
              key: org
        - name: OPENOBSERVE_TOKEN
          valueFrom:
            secretKeyRef:
              name: observability
              key: token
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

Deploy:

```bash
kubectl apply -f deployment.yaml
```

## Scalability Patterns

### Horizontal Scaling

The IVCAP platform automatically distributes jobs across service instances. Design your service to be stateless:

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    # Don't store state between jobs
    # Each job runs independently
    return Result(result=process(req.data))
```

### Resource Requirements

Specify resource needs in your service definition. The platform uses this for scheduling:

```python
from ivcap_service import ResourceRequirements

service = Service(
    name="GPU-Intensive Service",
    resources=ResourceRequirements(
        cpu=2,
        memory="4Gi",
        gpu=1  # Request GPU
    )
)
```

## Monitoring

### Health Checks

Implement health monitoring:

```bash
# Docker health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import ivcap_service; print('healthy')"
```

### Log Aggregation

Logs automatically export to OpenObserve. Query them:

```bash
# View service logs
ivcap logs -service my-service -hours 1
```

## Troubleshooting

### Container Won't Start

Check logs:

```bash
docker logs my-service
```

Ensure service code is correct:

```bash
# Test locally
docker run -it my-service:latest --print-service-description
```

### Jobs Failing

Check OpenObserve for logs and errors. Common issues:

1. Missing environment variables
2. Network connectivity to IVCAP
3. Insufficient resources
4. Unhandled exceptions

### Performance Issues

1. **Increase replicas** for more parallel processing
2. **Optimize code** to process faster
3. **Profile** using OpenObserve metrics
4. **Use caching** for expensive operations

## See Also

- [Best Practices](best-practices.md) — Production patterns
- [Observability](observability.md) — Monitoring setup
- [Error Handling](error-handling.md) — Robust error handling
