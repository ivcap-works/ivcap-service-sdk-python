SERVICE_FILE=secret.py
ROOT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

run:
	PYTHONPATH=../../src python ${SERVICE_FILE} \
	--secret-name test-OPENAPI-KEY

DOCKER_TAG=secret-example:latest

GIT_COMMIT ?= $(shell git rev-parse --short HEAD)
GIT_TAG ?= $(shell git describe --abbrev=0)

docker-build:
	docker build -t ${DOCKER_TAG} \
	--build-arg GIT_COMMIT=${GIT_COMMIT} \
	--build-arg GIT_TAG=${GIT_TAG} \
	-f ${ROOT_DIR}/Dockerfile \
	$(shell realpath ${ROOT_DIR}/../..)
