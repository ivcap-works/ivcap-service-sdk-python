FROM python:3.10-slim-buster

RUN pip install poetry

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false && poetry install --no-root

COPY batch_service.py .

# VERSION INFORMATION
ARG VERSION ???
ENV VERSION=$VERSION
ENV PORT=80

# Command to run
ENTRYPOINT ["python",  "/app/batch_service.py"]