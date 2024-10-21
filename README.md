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
from ivcap_sdk_service import Service, ServiceArgs, Parameter, PythonWorkflow, Type, register_service
import logging

SERVICE = Service(
    name = "Hello World",
    description = "Simple service which does a few simple things",
    parameters = [
        Parameter(name="msg", type=Type.STRING, description="Message to echo"),
        Parameter(name="times", type=Type.INT, default=2, description="Times to repeat"),
    ],
    workflow = PythonWorkflow(min_memory='2Gi', min_cpu='500m', min_ephemeral_storage='4Gi'),
)

def hello_world(args: ServiceArgs, logger: logging):
    for i in range(args.times):
        logger.info(f"({i + 1}) Hello {args.msg}")

register_service(SERVICE, hello_world)
```

For more useful examples see the [examples](https://github.com/ivcap-works/ivcap-service-sdk-python/tree/main/examples) directory or for a git repo which could work as a starting point, check out [ivcap-python-service-example](https://github.com/ivcap-works/ivcap-python-service-example) and [ivcap-python-service-example-collection](https://github.com/ivcap-works/ivcap-python-service-example-collection).

## API Documentation

The auto-generated API docs can be found [here](https://ivcap-works.github.io/ivcap-service-sdk-python/autoapi/index.html).

## Contributing

Interested in contributing? Check out the contributing guidelines. Please note that this project is released with a Code of Conduct. By contributing to this project, you agree to abide by its terms.

## License

`ivcap_sdk_service` was initially created by Max Ott <max.ott@csiro.au>, Tim Erwin <tim.erwin@csiro.au> with additional contributions from Ben Clews <ben.clews@csiro.au>" and
"John Zhang <j.zhang@csiro.au>". See [LICENSE](https://github.com/ivcap-works/ivcap-service-sdk-python/tree/main/LICENSE) for licensing terms.

## Credits

`ivcap_sdk_service` was created with [`cookiecutter`](https://cookiecutter.readthedocs.io/en/latest/) and the `py-pkgs-cookiecutter` [template](https://github.com/py-pkgs/py-pkgs-cookiecutter).

## Development

### Setup with Conda

To use `conda` to create a virtual python environment named `ivcap_service`:

```
conda create --name ivcap_service python=3.9 -y
conda activate ivcap_service
pip install poetry
```

### Setup with Nix Flakes

Alternatively, if you'd like to use [Nix Flakes](https://nixos.wiki/wiki/Flakes) for your
virtual environment, run:

```shell
nix develop
```

To use direnv to automatically load the development environment when you enter
the `ivcap-service-sdk-python` directory, run:

```shell
direnv allow
```

### Adding dependencies

For testing:

    poetry add --group dev _lib_name_
