SERVICE_FILE=secret.py
ROOT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

run:
	PYTHONPATH=../../src python ${SERVICE_FILE} \
	--secret-name test-OPENAPI-KEY

DOCKER_TAG=secret-example:latest

docker-build:
	docker build -t ${DOCKER_TAG} \
	--build-arg GIT_COMMIT=${GIT_COMMIT} \
	--build-arg GIT_TAG=${GIT_TAG} \
	--build-arg TIMEZONE=${BUILD_TZ} \
	-f ${ROOT_DIR}/Dockerfile \
	$(shell realpath ${ROOT_DIR}/../..)
