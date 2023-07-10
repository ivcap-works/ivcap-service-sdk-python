
SERVICE_FILE=img_test_service.py

GIT_COMMIT := $(shell git rev-parse --short HEAD)
GIT_TAG := $(shell git describe --abbrev=0 --tags ${TAG_COMMIT} 2>/dev/null || true)

PROJECT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

TMP_DIR=/tmp
IMG_URL=https://juststickers.in/wp-content/uploads/2016/07/go-programming-language.png

run-help:
	@PYTHONPATH=../../src python ${PROJECT_DIR}/${SERVICE_FILE} -H

run:
	mkdir -p ${PROJECT_DIR}/DATA
	python ${SERVICE_FILE} \
	  --msg "$(shell date "+%d/%m-%H:%M:%S")" \
		--bg-artifact ${IMG_URL} \
		--ivcap:out-dir ${PROJECT_DIR}/DATA \
		--ivcap:cache-dir ${PROJECT_DIR}/DATA/cache
	@echo ">>> Output should be in '${PROJECT_DIR}/DATA'"

run-no-cache:
	rm -rf ${PROJECT_DIR}/DATA/cache
	make -f ${PROJECT_DIR}/Makefile run

run-collection:
	mkdir -p ${PROJECT_DIR}/DATA
	python ${SERVICE_FILE} \
	  --msg "$(shell date "+%d/%m-%H:%M:%S")" \
		--backgrounds ${PROJECT_DIR}/backgrounds \
		--transparent-background \
		--ivcap:out-dir ${PROJECT_DIR}/DATA \
		--ivcap:cache-dir ${PROJECT_DIR}/DATA/cache
	@echo ">>> Output should be in '${PROJECT_DIR}/DATA'"

run-collection-single:
	mkdir -p ${PROJECT_DIR}/DATA
	python ${SERVICE_FILE} \
	  --msg "$(shell date "+%d/%m-%H:%M:%S")" \
		--backgrounds ${PROJECT_DIR}/backgrounds/python.png \
		--transparent-background \
		--ivcap:out-dir ${PROJECT_DIR}/DATA \
		--ivcap:cache-dir ${PROJECT_DIR}/DATA/cache
	@echo ">>> Output should be in '${PROJECT_DIR}/DATA'"

run-on-ivcap:
	rm -r ${PROJECT_DIR}/DATA && mkdir -p ${PROJECT_DIR}/DATA
	env IVCAP_INSIDE_CONTAINER=1 \
		IVCAP_ORDER_ID=8dd9006f-d1a5-4a6f-a4e2-c4b196ca14f5 \
		IVCAP_CACHE_URL=http://cache.local \
		IVCAP_STORAGE_URL=http://artifact.local \
		IVCAP_CACHE_DIR=${PROJECT_DIR}/DATA \
		http_proxy=http://localhost:8888 \
		https_proxy=http://localhost:8888 \
		python ${SERVICE_FILE} \
			--msg "$(shell date "+%d/%m-%H:%M:%S")" \
			--ivcap:in-dir ${PROJECT_DIR}/DATA \
			--ivcap:out-dir ${PROJECT_DIR}/DATA

run-debug:
	rm -r ${PROJECT_DIR}/DATA && mkdir -p ${PROJECT_DIR}/DATA
	env IVCAP_INSIDE_CONTAINER=1 \
		IVCAP_ORDER_ID=8dd9006f-d1a5-4a6f-a4e2-c4b196ca14f5 \
		IVCAP_CACHE_URL=http://cache.local \
		IVCAP_STORAGE_URL=http://localhost:8888 \
		IVCAP_CACHE_DIR=${PROJECT_DIR}/DATA \
		python ${SERVICE_FILE} \
			--msg "$(shell date "+%d/%m-%H:%M:%S")" \
			--ivcap:in-dir ${PROJECT_DIR}/DATA \
			--ivcap:out-dir ${PROJECT_DIR}/DATA
	@echo ">>> Output should be in '${PROJECT_DIR}/DATA'"


clean:
	rm -rf ${PROJECT_DIR}/$(shell echo ${SERVICE_FILE} | cut -d. -f1 ).dist
	rm -rf ${PROJECT_DIR}/$(shell echo ${SERVICE_FILE} | cut -d. -f1 ).build
	rm -rf ${PROJECT_DIR}/cache ${PROJECT_DIR}/DATA

FORCE:
