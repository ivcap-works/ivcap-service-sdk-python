
ROOT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
SRC_DIR:=${ROOT_DIR}/src

.PHONY: help build publish test lint typecheck fmt format check add-license clean docs docs-serve docs-clean

help:
	@echo "Targets:"
	@echo "  make setup       - Setup poetry, venv, and install all dependencies"
	@echo "  make build       - Build wheel/sdist (includes license header check)"
	@echo "  make publish     - Publish package via Poetry (requires configured credentials)"
	@echo "  make test        - Run tests"
	@echo "  make lint        - Run ruff checks"
	@echo "  make typecheck   - Run pyright type checking"
	@echo "  make fmt         - Format code with ruff"
	@echo "  make check       - Lint + tests"
	@echo "  make add-license - Ensure license headers are present"
	@echo "  make docs        - Build documentation"
	@echo "  make docs-serve  - Serve documentation locally (http://localhost:8000)"
	@echo "  make docs-clean  - Clean built documentation"
	@echo "  make clean       - Remove build artifacts + caches"

setup:
	poetry config virtualenvs.in-project true --local
	poetry install

build: add-license
	cd ${ROOT_DIR}
	rm -rf ${ROOT_DIR}/dist/*
	poetry build

# https://www.digitalocean.com/community/tutorials/how-to-publish-python-packages-to-pypi-using-poetry-on-ubuntu-22-04
publish: build
	poetry publish

test:
	poetry run pytest ${ROOT_DIR}/tests/ --cov=ivcap_service --cov-report=xml

lint:
	poetry run poe lint

typecheck:
	poetry run poe typecheck

fmt format:
	poetry run poe format

check: lint typecheck test

add-license:
	poetry run licenseheaders -t .license.tmpl -y $(shell date +%Y) -f ivcap_service/*.py -f tests/*.py

clean:
	rm -rf *.egg-info
	rm -rf dist
	find ${ROOT_DIR} -name __pycache__ | xargs rm -r

docs:
	@echo "Building documentation..."
	poetry run poe docs

docs-serve:
	@echo "Serving documentation at http://localhost:8000"
	cd docs && poetry run mkdocs serve

docs-clean:
	@echo "Cleaning documentation..."
	poetry run poe docs-clean
