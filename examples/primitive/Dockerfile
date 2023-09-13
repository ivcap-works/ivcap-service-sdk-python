# Stage 1: Build the Go binary
FROM golang:1.21-alpine AS build

# Install Git. Required for fetching the dependencies.
RUN apk add --no-cache git

ENV GOOS=linux
ENV GO111MODULE=on

# Set the Current Working Directory inside the container
WORKDIR /primitive

# Copy everything from the current directory to the Working Directory inside the container
COPY . .

# Install the primitive package
RUN go install github.com/bclews/primitive@latest

# Stage 2: Create a lightweight image with the Go binary and Python script
FROM alpine:3.18

# Install Python and pip
RUN apk add --no-cache python3 py3-pip

# Copy the Go binary from the builder stage
COPY --from=build /go/bin/primitive /usr/bin/primitive

# Copy the requirements file into the Docker image
COPY requirements.txt /primitive/

# Install Python packages from the requirements file
RUN pip3 install -r /primitive/requirements.txt

# Copy your Python script into the Docker image (replace 'your_script.py' with the actual filename)
COPY service.py /primitive/

VOLUME /app
WORKDIR /app

# Run your Python script (replace 'your_script.py' with the actual filename)
ENTRYPOINT ["python", "/primitive/service.py"]
