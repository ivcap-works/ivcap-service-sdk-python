FROM python:3.10-slim-bullseye

WORKDIR /app
RUN pip install -U pip
COPY examples/secret/requirements.txt ./
RUN pip install -r requirements.txt --force-reinstall

# Get service files
COPY src ./src
COPY examples/secret/secret.py ./service.py

ENV PYTHONPATH="/app/src"

# VERSION INFORMATION
ARG GIT_TAG
ARG GIT_COMMIT

ENV IVCAP_SERVICE_VERSION=$GIT_TAG
ENV IVCAP_SERVICE_COMMIT=$GIT_COMMIT
ENTRYPOINT ["python", "/app/service.py"]