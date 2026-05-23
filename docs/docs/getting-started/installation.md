# Installation

## Prerequisites

- Python 3.10 or higher
- pip or poetry package manager

## From PyPI

The easiest way to install the IVCAP Service SDK:

```bash
pip install ivcap_service
```

Or with poetry:

```bash
poetry add ivcap_service
```

## From Source

For development or to use the latest unreleased features:

```bash
git clone https://github.com/ivcap-works/ivcap-service-sdk-python.git
cd ivcap-service-sdk-python
poetry install
```

## Verify Installation

Test your installation:

```bash
python -c "import ivcap_service; print(ivcap_service.__version__)"
```

You should see the version number printed.

## Optional: Development Dependencies

If you plan to contribute or build documentation locally:

```bash
# Development tools
poetry install --with dev

# Documentation tools
pip install -r docs/requirements-docs.txt
```

## Next Steps

- Read the [Quick Start](quick-start.md) guide
- Build your [First Service](first-service.md)
- Check out [Examples](../examples/batch-service.md)

## Troubleshooting

### ImportError: No module named 'ivcap_service'

Make sure you've installed the package:
```bash
pip install ivcap_service
```

If using a virtual environment, ensure it's activated.

### Python Version Error

Check your Python version:
```bash
python --version
```

The SDK requires Python 3.10+. If you have multiple Python versions installed, use:
```bash
python3.10 -m pip install ivcap_service
```

### Permission Denied

If you get permission errors during installation, use:
```bash
pip install --user ivcap_service
```

## Getting Help

- Check [Common Issues](../guides/best-practices.md#troubleshooting)
- [Open an issue](https://github.com/ivcap-works/ivcap-service-sdk-python/issues)
- See [Contributing](../community/contributing.md)
