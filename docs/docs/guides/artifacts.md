# Working with Artifacts

This guide covers downloading, uploading, and managing artifacts in your IVCAP services
using the `ctxt.ivcap` client available inside every job.

## Overview

An **Artifact** is any binary or structured data blob consumed or produced by a job:
an image, a CSV file, a NetCDF dataset, a trained model checkpoint, etc.

Your services commonly:

- Download input artifacts passed in as request parameters
- Upload results as new artifacts
- Organize artifacts in collections
- Attach typed metadata (aspects) to artifacts

> **`ctxt.ivcap` is always available** inside a job worker function.
> It is pre-configured with the platform-injected credentials — no explicit
> authentication is needed.

## Accessing the IVCAP Client

```python
def process_job(req: Request, ctxt: JobContext) -> Result:
    ivcap = ctxt.ivcap  # property — no parentheses
    ...
```

## Downloading Artifacts

Three methods are available, each suited to a different use case:

| Method | Best for |
|---|---|
| `artifact.as_local_file()` | **Recommended** — saves to disk with minimal code |
| `artifact.open()` | Loading small artifacts entirely into memory |
| `artifact.as_stream()` | Custom chunk processing or piping into external APIs |

### Download to a local file (recommended)

`as_local_file()` handles all streaming internals for you and supports two patterns:

**Temporary file** (auto-deleted when the `with` block exits):

```python
def process_job(req: Request, ctxt: JobContext) -> Result:
    ivcap = ctxt.ivcap

    artifact = ivcap.get_artifact(req.input_artifact_urn)

    with artifact.as_local_file() as path:
        logger.info(f"Downloaded to: {path}")
        data = path.read_bytes()
        result = process(data)
    # temp file deleted here

    return Result(result=result)
```

**Explicit path** (file is kept after the `with` block):

```python
def process_job(req: Request, ctxt: JobContext) -> Result:
    ivcap = ctxt.ivcap

    artifact = ivcap.get_artifact(req.input_artifact_urn)
    path = artifact.as_local_file("/tmp/input.csv")

    logger.info(f"Saved to: {path}")
    result = process_csv(path)

    return Result(result=result)
```

**Explicit path with a suggested name** (useful when you want the SDK to choose the
directory but control the filename):

```python
with artifact.as_local_file("my_input.jpg") as path:
    img = Image.open(path)
```

### Open as an in-memory file object

```python
def process_job(req: Request, ctxt: JobContext) -> Result:
    ivcap = ctxt.ivcap

    artifact = ivcap.get_artifact(req.input_artifact_urn)

    with artifact.open() as f:
        data = f.read()           # bytes
        text = data.decode("utf-8")

    return Result(result=process(text))
```

!!! warning
    `open()` loads the entire blob into memory.  For large artifacts
    (hundreds of MB+) prefer `as_local_file()` or `as_stream()`.

### Stream in chunks (advanced)

Use `as_stream()` when you need low-level control: progress reporting, piping bytes
into a third-party API, or incremental processing.

```python
def process_job(req: Request, ctxt: JobContext) -> Result:
    ivcap = ctxt.ivcap

    artifact = ivcap.get_artifact(req.input_artifact_urn)

    total = 0
    with open("/tmp/output.bin", "wb") as f:
        for chunk in artifact.as_stream():
            f.write(chunk)
            total += len(chunk)

    logger.info(f"Downloaded {total} bytes")
    return Result(result=process_file("/tmp/output.bin"))
```

## Uploading Artifacts

### Upload from an in-memory stream

```python
import io

def process_job(req: Request, ctxt: JobContext) -> Result:
    ivcap = ctxt.ivcap

    result_data = process(req.data)

    artifact = ivcap.upload_artifact(
        name="my-result.json",
        io_stream=io.BytesIO(result_data),
        content_type="application/json",
        content_size=len(result_data),
    )

    logger.info(f"Uploaded artifact: {artifact.id}")
    return Result(artifact_urn=artifact.id)
```

### Upload a local file

```python
def process_job(req: Request, ctxt: JobContext) -> Result:
    ivcap = ctxt.ivcap

    # Write output to a temp file
    output_path = "/tmp/result.csv"
    with open(output_path, "w") as f:
        f.write(generate_csv(req.data))

    # Upload the file
    artifact = ivcap.upload_artifact(
        name="result.csv",
        file_path=output_path,
        content_type="text/csv",
    )

    logger.info(f"Uploaded: {artifact.id}")
    return Result(artifact_urn=artifact.id)
```

### Upload parameters

| Parameter | Type | Description |
|---|---|---|
| `name` | `str` | Human-readable name for the artifact |
| `file_path` | `str` | Local path to upload |
| `io_stream` | `IO` | In-memory stream (requires `content_type`) |
| `content_type` | `str` | MIME type (auto-detected from `file_path` extension if omitted) |
| `content_size` | `int` | Size in bytes (-1 = unknown) |
| `collection` | `URN` | Add to a named collection (`urn:ivcap:collection:...`) |
| `policy` | `URN` | Access policy (`urn:ivcap:policy:...`) |

## Adding Metadata (Aspects) to Artifacts

Attach structured domain metadata to any artifact in the Datafabric:

```python
def process_job(req: Request, ctxt: JobContext) -> Result:
    ivcap = ctxt.ivcap

    artifact = ivcap.get_artifact(req.artifact_urn)

    # Attach custom metadata
    ivcap.add_aspect(
        entity=artifact.id,
        aspect={
            "$schema": "urn:my-service:schema:processing-result.1",
            "processed_by": "my-service",
            "processing_time_seconds": 42.5,
            "status": "success",
            "tags": ["important", "verified"],
        },
    )

    return Result(artifact_urn=artifact.id)
```

## Common Patterns

### Download → Process → Upload pipeline

```python
def process_job(req: Request, ctxt: JobContext) -> Result:
    ivcap = ctxt.ivcap

    with ctxt.report.step("load", msg="Downloading input") as s:
        artifact = ivcap.get_artifact(req.input_urn)
        with artifact.as_local_file() as path:
            data = path.read_bytes()
        s.finished(msg=f"Downloaded {len(data)} bytes")

    with ctxt.report.step("transform", msg="Transforming") as s:
        transformed = transform(data)
        s.finished(msg=f"Transformed {len(data)} bytes")

    with ctxt.report.step("validate", msg="Validating") as s:
        validate(transformed)
        s.finished()

    with ctxt.report.step("save", msg="Uploading result") as s:
        import io
        output_artifact = ivcap.upload_artifact(
            name="result.bin",
            io_stream=io.BytesIO(transformed),
            content_type="application/octet-stream",
            content_size=len(transformed),
        )
        s.finished(msg=f"Uploaded {output_artifact.id}")

    return Result(output_urn=output_artifact.id)
```

### Batch upload to a collection

```python
import io

def process_job(req: Request, ctxt: JobContext) -> Result:
    ivcap = ctxt.ivcap
    collection_id = "urn:ivcap:collection:batch-results"
    artifact_urns = []

    with ctxt.report.step("batch_processing", msg="Processing items") as step:
        for i, item in enumerate(req.items):
            processed = process(item)
            artifact = ivcap.upload_artifact(
                name=f"item-{i}.bin",
                io_stream=io.BytesIO(processed),
                content_type="application/octet-stream",
                content_size=len(processed),
                collection=collection_id,
            )
            artifact_urns.append(artifact.id)

            if i % 100 == 0:
                step.info(event={"processed": i, "total": len(req.items)})

        step.finished(msg=f"Uploaded {len(artifact_urns)} artifacts")

    return Result(artifact_urns=artifact_urns)
```

### Streaming large files

For very large files, stream directly to disk using `as_local_file()` or process
chunks with `as_stream()`:

```python
import io

def process_job(req: Request, ctxt: JobContext) -> Result:
    ivcap = ctxt.ivcap

    artifact = ivcap.get_artifact(req.input_urn)

    with ctxt.report.step("process", msg="Streaming large file") as step:
        processed_chunks = []
        bytes_read = 0

        for chunk in artifact.as_stream():
            processed = process_chunk(chunk)
            processed_chunks.append(processed)
            bytes_read += len(chunk)

            if bytes_read % (10 * 1024 * 1024) == 0:  # every 10 MB
                step.info(event={"bytes_read": bytes_read})

        step.finished(msg=f"Processed {bytes_read} bytes")

    with ctxt.report.step("upload", msg="Uploading result") as step:
        final_data = b"".join(processed_chunks)
        result_artifact = ivcap.upload_artifact(
            name="processed-output.bin",
            io_stream=io.BytesIO(final_data),
            content_type="application/octet-stream",
            content_size=len(final_data),
        )
        step.finished(msg=f"Uploaded {result_artifact.id}")

    return Result(artifact_urn=result_artifact.id)
```

## Error Handling

```python
from ivcap_client.exception import ResourceNotFound, IvcapApiError

def process_job(req: Request, ctxt: JobContext) -> Result:
    ivcap = ctxt.ivcap

    with ctxt.report.step("download", msg="Downloading") as step:
        try:
            artifact = ivcap.get_artifact(req.input_urn)
            with artifact.as_local_file() as path:
                data = path.read_bytes()
            step.finished(msg=f"Downloaded {len(data)} bytes")
        except ResourceNotFound:
            logger.warning(f"Artifact not found: {req.input_urn}, using default data")
            step.finished(msg="Using default data")
            data = DEFAULT_DATA
        except IvcapApiError as e:
            logger.error(f"Platform API error [{e.status_code}]: {e}")
            raise

    with ctxt.report.step("upload", msg="Uploading") as step:
        try:
            import io
            result_artifact = ivcap.upload_artifact(
                name="result.bin",
                io_stream=io.BytesIO(process(data)),
                content_type="application/octet-stream",
            )
            step.finished(msg=f"Uploaded {result_artifact.id}")
        except IvcapApiError as e:
            logger.error(f"Upload failed [{e.status_code}]: {e}")
            raise

    return Result(artifact_urn=result_artifact.id)
```

## See Also

- [Job Processing](job-processing.md) — Core patterns
- [Service Composition](service-composition.md) — Calling other services
- [Deployment](deployment.md) — Production setup
- [ivcap-client SDK — Artifacts](https://ivcap-works.github.io/ivcap-client-sdk-python/guides/artifacts/) — Full client-side artifact reference
