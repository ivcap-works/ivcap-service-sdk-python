# Working with Artifacts Guide

This guide covers downloading, uploading, and managing artifacts in your IVCAP services.

## Overview

Artifacts are files or data objects stored in the IVCAP platform. Your services commonly:
- Download input artifacts for processing
- Upload results as artifacts
- Organize artifacts in collections
- Add metadata (tags, aspects) to artifacts

## Downloading Artifacts

### Basic Download

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    ivcap = ctx.ivcap()
    if not ivcap:
        raise RuntimeError("IVCAP not available")

    # Download artifact data
    artifact_data = ivcap.artifact(req.input_artifact_id).read()

    # Process the data
    result = process(artifact_data)

    return Result(result=result)
```

### Downloading to File

```python
import tempfile
import os

def process_job(req: Request, ctx: JobContext) -> Result:
    ivcap = ctx.ivcap()

    # Download to temporary file
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        artifact = ivcap.artifact(req.input_artifact_id)
        # Download to file
        for chunk in artifact.iter_content():
            tmp.write(chunk)
        tmp_path = tmp.name

    try:
        # Process file
        result = process_file(tmp_path)
    finally:
        os.unlink(tmp_path)

    return Result(result=result)
```

## Uploading Artifacts

### Upload Bytes

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    ivcap = ctx.ivcap()

    # Process data
    result_data = process(req.data)

    # Upload as artifact
    artifact_id = ivcap.artifact_new(
        data=result_data,
        collection_id=None,  # Optional
        tags=["processed"]
    )

    return Result(artifact_id=artifact_id)
```

### Upload File

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    ivcap = ctx.ivcap()

    # Process and save to file
    output_file = "/tmp/result.txt"
    with open(output_file, "w") as f:
        f.write(process(req.data))

    # Upload file
    with open(output_file, "rb") as f:
        artifact_id = ivcap.artifact_new(
            data=f.read(),
            collection_id=None,
            tags=["result"]
        )

    return Result(artifact_id=artifact_id)
```

## Collections

Organize artifacts in collections:

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    ivcap = ctx.ivcap()

    # Create or get collection
    collection_id = "urn:ivcap:collection:results"

    results = []
    for item in req.items:
        data = process(item)
        artifact_id = ivcap.artifact_new(
            data=data,
            collection_id=collection_id,  # Add to collection
            tags=["item", f"index-{len(results)}"]
        )
        results.append(artifact_id)

    return Result(artifacts=results)
```

## Tagging and Metadata

Add tags for organization:

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    ivcap = ctx.ivcap()

    result_data = process(req.data)

    artifact_id = ivcap.artifact_new(
        data=result_data,
        collection_id=None,
        tags=[
            "processed",
            "version-2",
            f"user-{req.user_id}",
            "timestamp-2024-05-23"
        ]
    )

    return Result(artifact_id=artifact_id)
```

## Common Patterns

### Pipeline Processing

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    ivcap = ctx.ivcap()

    with ctx.report.step("load") as s:
        input_data = ivcap.artifact(req.input_id).read()
        s.finished()

    with ctx.report.step("transform") as s:
        transformed = transform(input_data)
        s.finished()

    with ctx.report.step("validate") as s:
        validate(transformed)
        s.finished()

    with ctx.report.step("save") as s:
        output_id = ivcap.artifact_new(
            data=transformed,
            tags=["validated"]
        )
        s.finished()

    return Result(output_id=output_id)
```

### Batch Upload

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    ivcap = ctx.ivcap()
    collection_id = "urn:ivcap:collection:batch-results"
    results = []

    with ctx.report.step("batch_processing") as step:
        for i, item in enumerate(req.items):
            processed = process(item)
            artifact_id = ivcap.artifact_new(
                data=processed,
                collection_id=collection_id,
                tags=[f"batch-item-{i}"]
            )
            results.append(artifact_id)

            if i % 100 == 0:
                step.info(event={"processed": i})

        step.finished()

    return Result(artifact_ids=results)
```

### Streaming Large Files

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    ivcap = ctx.ivcap()

    # Download in chunks
    input_data = ivcap.artifact(req.input_id).read()

    # Process in chunks
    output_chunks = []
    for chunk in iter_chunks(input_data, chunk_size=1MB):
        processed_chunk = process_chunk(chunk)
        output_chunks.append(processed_chunk)

    # Combine and upload
    final_data = b"".join(output_chunks)
    artifact_id = ivcap.artifact_new(data=final_data)

    return Result(artifact_id=artifact_id)
```

## Error Handling

```python
def process_job(req: Request, ctx: JobContext) -> Result:
    ivcap = ctx.ivcap()

    try:
        # Download
        artifact = ivcap.artifact(req.input_id).read()
    except Exception as e:
        ctx.report.step("download").error(e)
        raise

    try:
        # Process
        result = process(artifact)
    except Exception as e:
        ctx.report.step("processing").error(e)
        raise

    try:
        # Upload
        artifact_id = ivcap.artifact_new(data=result)
    except Exception as e:
        ctx.report.step("upload").error(e)
        raise

    return Result(artifact_id=artifact_id)
```

## See Also

- [Job Processing](job-processing.md) — Core patterns
- [Service Composition](service-composition.md) — Calling other services
- [Deployment](deployment.md) — Production setup
