# ivcap_sdk_service

SDK library for building services for the IVCAP platform

## Installation

```bash
pip install ivcap_sdk_service
```

## Usage

For example use cases see the [examples](./examples) directory.

## Contributing

Interested in contributing? Check out the contributing guidelines. Please note that this project is released with a Code of Conduct. By contributing to this project, you agree to abide by its terms.

## License

`ivcap_sdk_service` was created by Max Ott <max.ott@csiro.au>, Tim Erwin <tim.erwin@csiro.au>. It is licensed under the terms of a Proprietary license.

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
