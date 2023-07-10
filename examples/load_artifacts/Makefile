
SERVICE_FILE=load_artifacts.py

PROJECT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

IMG_URL=https://juststickers.in/wp-content/uploads/2016/07/go-programming-language.png

run-help:
	@PYTHONPATH=../../src python ${PROJECT_DIR}/${SERVICE_FILE} -H

run:
	mkdir -p ${PROJECT_DIR}/DATA
	PYTHONPATH=../../src python ${PROJECT_DIR}/${SERVICE_FILE} \
	  --load ${IMG_URL} \
		--ivcap:out-dir ${PROJECT_DIR}/DATA \
		--ivcap:cache-dir ${PROJECT_DIR}/DATA/cache
	@echo ">>> Output should be in '${PROJECT_DIR}/DATA'"

run-no-cache:
	rm -rf ${PROJECT_DIR}/DATA/cache
	make -f ${PROJECT_DIR}/Makefile run

run-remote:
	PYTHONPATH=../../src python ${PROJECT_DIR}/${SERVICE_FILE} \
	  --load ${IMG_URL} \
		--ivcap:storage-url http://localhost:4000


clean:
	rm -rf ${PROJECT_DIR}/$(shell echo ${SERVICE_FILE} | cut -d. -f1 ).dist
	rm -rf ${PROJECT_DIR}/$(shell echo ${SERVICE_FILE} | cut -d. -f1 ).build
	rm -rf ${PROJECT_DIR}/cache ${PROJECT_DIR}/DATA
