# Test Batch Service

A batch tool primarily used for load testing the IVCAP platform.

## Docker Build Options

This example supports two Docker build methods:

### 1. Build with Published Library (Production)

Uses the published `ivcap_service` library from PyPI (as specified in `pyproject.toml`).

**Dockerfile:** `Dockerfile`
**Build command:**
```bash
make docker-build-published
```

Or manually:
```bash
docker build -f Dockerfile -t test-batch:published --build-arg VERSION=0.1.0 .
```

### 2. Build with Local Source Code (Development)

Uses the local `ivcap_service` source code from the repository root instead of the published version. This is useful for:
- Testing changes to the SDK before publishing
- Development and debugging
- Ensuring compatibility with unreleased SDK features

**Dockerfile:** `Dockerfile.local`
**Build command:**
```bash
make docker-build-local
```

Or manually:
```bash
cd examples/test-batch
docker build -f Dockerfile.local -t test-batch:local-src --build-arg VERSION=dev ../../
```

**Note:** The build context must be the repository root (`../../`) to access the SDK source code.

### Run the Local Build

```bash
make docker-run-local
```

Or manually:
```bash
docker run -it -p 8095:80 -e IVCAP_BASE_URL="http://ivcap.local" --rm test-batch:local-src
```

## Local Development (Without Docker)

Run the service locally using poetry:

```bash
make run
```

This uses `PYTHONPATH` to reference the local SDK source code.

## Testing

Test against a running IVCAP instance:

```bash
make test-ivcap
```

Stream job execution:

```bash
make test-ivcap-stream
```
