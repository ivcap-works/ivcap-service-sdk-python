# Contributing

We welcome contributions to the IVCAP Service SDK!

## Getting Started

### 1. Fork and Clone

```bash
git clone https://github.com/YOUR_USERNAME/ivcap-service-sdk-python.git
cd ivcap-service-sdk-python
```

### 2. Set Up Development Environment

```bash
poetry install --with dev
```

### 3. Create a Branch

```bash
git checkout -b feature/my-feature
```

## Development Workflow

### Running Tests

```bash
poetry run pytest
pytest --cov
```

### Code Quality

```bash
# Format code
poetry run ruff format .

# Lint
poetry run ruff check . --fix

# Type checking
poetry run pyright
```

### Building Documentation

```bash
cd docs
pip install -r requirements-docs.txt
mkdocs serve
```

Visit `http://localhost:8000` to preview the docs.

## Making Changes

### Code Changes

1. Make your changes in a feature branch
2. Add tests for new functionality
3. Ensure all tests pass: `poetry run pytest`
4. Update documentation as needed

### Documentation Changes

1. Edit files in `docs/docs/`
2. Test locally: `mkdocs serve`
3. Check formatting and links
4. Submit pull request

## Commit Messages

Use clear, descriptive commit messages:

```
✨ feat: add new feature
🐛 fix: resolve bug
📝 docs: update documentation
🧪 test: add unit tests
🔨 chore: refactor code
```

## Pull Request Process

1. Update documentation
2. Add/update tests
3. Ensure CI passes
4. Create clear PR description
5. Link related issues

## Code Style

We follow Python PEP 8 with these tools:

- **Ruff** — Linting and formatting
- **Pyright** — Type checking
- **Pytest** — Testing

### Style Guide

```python
# Docstrings follow Google style
def process_job(req: Request, ctx: JobContext) -> Result:
    """
    Process a job.

    Args:
        req: Request to process
        ctx: Job context

    Returns:
        Processing result

    Raises:
        ValueError: If validation fails
    """
    pass

# Type hints required
def add(a: int, b: int) -> int:
    return a + b

# Use meaningful variable names
result = process(data)  # Good
x = process(y)          # Bad
```

## Testing

Write tests for new features:

```python
# tests/test_feature.py
import pytest
from src.feature import my_function

def test_my_function_basic():
    result = my_function(5)
    assert result == 10

def test_my_function_error():
    with pytest.raises(ValueError):
        my_function(-1)
```

Run tests:

```bash
poetry run pytest tests/
poetry run pytest tests/test_feature.py -v
```

## Documentation Guidelines

1. **Be clear** — Write for developers new to the SDK
2. **Include examples** — Every concept should have a code example
3. **Link between pages** — Use relative links to other docs
4. **Update TOC** — If adding new pages, update mkdocs.yml

## Reporting Issues

### Bug Reports

Include:
- Minimal reproducible example
- Expected vs actual behavior
- Python version and environment
- Traceback (if applicable)

### Feature Requests

Include:
- Use case and motivation
- Proposed API/syntax
- Any alternatives considered

## Questions?

- **GitHub Issues** — For bugs and feature requests
- **Discussions** — For questions and ideas
- **Email** — For security issues

## License

By contributing, you agree that your contributions will be licensed under the same [LICENSE](../../LICENSE) as the project.

---

Thank you for contributing to IVCAP! 🚀
