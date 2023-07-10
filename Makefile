
DOCKER_NAME=ivcap/sdk-server-python

# Git information
GIT_COMMIT := $(shell git rev-parse --short HEAD)
GIT_REPOSITORY := $(shell git config --get remote.origin.url)
GIT_TAG := $(shell git describe --abbrev=0 --tags ${GIT_COMMIT} 2>/dev/null || true)

# Docker image information
DOCKER_REGISTRY=cipmain.azurecr.io
DOCKER_TAG=${DOCKER_NAME}:${GIT_TAG}
DOCKER_DEPLOY=${DOCKER_REGISTRY}/${DOCKER_TAG}
DOCKER_BILD_ARGS=--build-arg GIT_REVISION=${GIT_REVISION} --build-arg GIT_REPOSITORY=${GIT_REPOSITORY}

ROOT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

build: add-license
	poetry build

test:
	pytest ${ROOT_DIR}/tests/

docker-build:
	@echo "\nStarting build of docker image ${DOCKER_NAME}"
	docker build -t ${DOCKER_NAME} \
		--build-arg GIT_COMMIT=${GIT_COMMIT} \
		--build-arg GIT_TAG=${GIT_TAG} \
		-f ${ROOT_DIR}/Dockerfile ${ROOT_DIR} ${DOCKER_BILD_ARGS}
	# docker image tag ${DOCKER_NAME} ${DOCKER_NAME}:latest
	# docker image tag ${DOCKER_NAME} ${DOCKER_TAG}
	@echo "\nFinished building docker image ${DOCKER_NAME}"

docker-publish:
	@echo "\nPublishing docker image ${DOCKER_TAG}"
	docker image tag ${DOCKER_TAG} ${DOCKER_DEPLOY}
	docker image push ${DOCKER_DEPLOY}
	@echo "\nFinished publishing docker image ${DOCKER_DEPLOY}"

docker-run: #docker-build
	docker run -it \
		-e IVCAP_ORDER_ID=ivcap:order:0000 \
		-e IVCAP_NODE_ID=n0 \
		${DOCKER_NAME} \
			--msg World

add-license:
	licenseheaders -t .license.tmpl -y 2023 -d src
	licenseheaders -t .license.tmpl -y 2023 -d examples

docs:
	cd ${ROOT_DIR}/docs && make html

clean:
	rm -rf *.egg-info
	rm -rf dist
	find ${ROOT_DIR} -name __pycache__ | xargs rm -r 

.PHONY: docs