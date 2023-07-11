# ivcap_sdk_service

SDK library for building services for the IVCAP platform

## Installation

```bash
pip install ivcap_sdk_service
```

## Usage

Below is the obligatory _hello world_ service which simply writes a
few messages to logging.

```python
from typing import Dict
from ivcap_sdk_service import Service, Parameter, PythonWorkflow, Type, register_service
import logging

SERVICE = Service(
    name = "HelloWorld",
    description = "Simple service which does a few simple things",
    parameters = [
        Parameter(name="msg", type=Type.STRING, description="Message to echo"),
        Parameter(name="times", type=Type.INT, default=2, description="Times to repeat"),
    ],
    workflow = PythonWorkflow(min_memory='2Gi')
)

def hello_world(args: Dict, logger: logging):
    for i in range(args.times):
        logger.info(f"({i + 1}) Hello {args.msg}")

register_service(SERVICE, hello_world)
```

For more useful examples see the [examples](./examples) directory.

## Contributing

Interested in contributing? Check out the contributing guidelines. Please note that this project is released with a Code of Conduct. By contributing to this project, you agree to abide by its terms.

## License

`ivcap_sdk_service` was created by Max Ott <max.ott@csiro.au>, Tim Erwin <tim.erwin@csiro.au>. See [LICENSE](./LICENSE) for licensing terms.

## Credits

`ivcap_sdk_service` was created with [`cookiecutter`](https://cookiecutter.readthedocs.io/en/latest/) and the `py-pkgs-cookiecutter` [template](https://github.com/py-pkgs/py-pkgs-cookiecutter).

## Development

### Setup

```
conda create --name ivcap_service python=3.7 -y
conda activate ivcap_service
pip install poetry
```

### Adding dependencies

For testing:

    poetry add --group dev _lib_name_
