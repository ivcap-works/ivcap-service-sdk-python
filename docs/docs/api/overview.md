# API Reference Overview

The API reference documentation is automatically generated from the Python source code docstrings using [mkdocstrings](https://mkdocstrings.github.io/). This ensures the documentation stays in sync with the actual code.

## Main Classes

### Service
Defines service metadata, contact information, and configuration. Used to describe your service to the IVCAP platform.

See: [Service](service.md)

### JobContext
Provides access to job metadata, progress reporting, and IVCAP platform APIs during job execution. Passed to your job processing function.

See: [JobContext](job-context.md)

### Events & Reporting
Classes for reporting job progress, steps, and events back to the platform.

See: [Events & Reporting](events.md)

## Additional Resources

- **Types**: [Common type definitions and data models](types.md)
- **Utilities**: [Helper functions for logging and common operations](utilities.md)

## Documentation Style

All API documentation follows Google-style docstrings for consistency:
- Clear parameter descriptions
- Return type documentation
- Usage examples in docstrings
- Attribute documentation

The documentation is generated programmatically from the source code, not written manually, so it always reflects the current implementation.
