#
# Copyright (c) 2025 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
"""
Artifact download/(optional) re-upload worker function (used for the
'artifact' section of a 'test-batch' Request).
"""

import io
import os
from collections.abc import Iterator
from typing import IO, cast

from pydantic import BaseModel, Field

from ivcap_service import JobContext

DEFAULT_ARTIFACT_CHUNK_SIZE_BYTES = 1_048_576  # 1MB


class ArtifactTester(BaseModel):
    artifact_urn: str = Field(
        ..., description="URN of the artifact to download, e.g. 'urn:ivcap:artifact:...'."
    )
    upload_also: bool | None = Field(
        False,
        description="if True, re-upload the downloaded data as a new artifact",
    )
    chunk_size_bytes: int | None = Field(
        DEFAULT_ARTIFACT_CHUNK_SIZE_BYTES,
        description=(
            "size (in bytes) of each chunk read from the source artifact and, "
            "if 'upload_also' is set, immediately uploaded as a new chunk-artifact. "
            "Defaults to 1MB. Lower this to exercise chunkwise down/upload with "
            "small test artifacts, or raise it for larger artifacts that would "
            "otherwise not fit comfortably in memory as a single blob."
        ),
    )


class ArtifactResult(BaseModel):
    artifact_urn: str = Field(..., description="URN of the artifact that was downloaded")
    name: str | None = Field(None, description="name of the downloaded artifact")
    mime_type: str | None = Field(None, description="mime type of the downloaded artifact")
    downloaded_bytes: int = Field(..., description="total number of bytes downloaded")
    chunk_count: int = Field(..., description="number of chunks the download was split into")
    chunk_size_bytes: int = Field(..., description="size (in bytes) used for each chunk")
    uploaded_artifact_urn: str | None = Field(
        None,
        description=(
            "URN of the newly created artifact, if 'upload_also' was set on the request"
        ),
    )


class _SequentialReadStream:
    """A minimal, forward-only, sequential-read file-like adapter.

    Wraps a byte-chunk iterator (e.g. ``Artifact.as_stream()``) so it can be
    handed directly to ``ivcap.upload_artifact()``'s TUS-based ``io_stream``
    upload. The TUS uploader reads the stream in ``chunk_size``-sized
    pieces, issuing one PATCH request per chunk against a *single* upload
    session - so each downloaded chunk is appended straight onto the
    *same* destination artifact as soon as it arrives. Only one chunk is
    ever held in memory, no local disk is used, and exactly one new
    artifact results.

    ``tusclient`` probes the file size once via ``seek(0)``, then
    ``seek(0, SEEK_END)``, then ``tell()`` (see
    ``BaseUploader.get_file_size``/``get_file_stream``) - without any
    ``read()`` in between - and, before every chunk read, issues a
    ``seek(0)`` immediately followed by ``seek(<current offset>)`` (see
    ``BaseTusRequest.__init__``). We track whichever of "seek-to-end" or
    "seek-to-offset" was requested *last*, so ``tell()``/``read()`` always
    see the intended position even though a redundant ``seek(0)`` precedes
    both patterns. True random access is not supported - only the
    sequential access pattern tus actually performs.
    """

    def __init__(self, chunk_iter: Iterator[bytes], total_size: int):
        self._chunk_iter = chunk_iter
        self._total_size = total_size
        self._buffer = b""
        self._delivered = 0  # bytes already handed out via read()
        self._wanted_pos: int = 0
        self._at_end = False

    def seek(self, pos: int, whence: int = 0) -> int:
        if whence == os.SEEK_END:
            self._at_end = True
            return self._total_size
        if whence != os.SEEK_SET:
            raise NotImplementedError("only SEEK_SET/SEEK_END are supported")
        self._at_end = False
        self._wanted_pos = pos
        return pos

    def tell(self) -> int:
        return self._total_size if self._at_end else self._wanted_pos

    def read(self, n: int = -1) -> bytes:
        if not self._at_end and self._wanted_pos != self._delivered:
            raise ValueError(
                "_SequentialReadStream only supports sequential, forward-only "
                f"reads; requested position {self._wanted_pos} but "
                f"{self._delivered} bytes have already been delivered."
            )
        while n < 0 or len(self._buffer) < n:
            try:
                self._buffer += next(self._chunk_iter)
            except StopIteration:
                break
        if n < 0:
            data, self._buffer = self._buffer, b""
        else:
            data, self._buffer = self._buffer[:n], self._buffer[n:]
        self._delivered += len(data)
        self._wanted_pos = self._delivered
        return data


def handle_artifact(req: ArtifactTester, ctxt: JobContext) -> ArtifactResult:
    """
    Downloads the artifact identified by 'req.artifact_urn' in fixed-size
    chunks (of 'req.chunk_size_bytes' bytes, default 1MB) and, if
    'req.upload_also' is set, streams each chunk straight into a SINGLE
    new artifact - one TUS PATCH request per chunk, appended to the same
    upload session - as soon as it is downloaded.

    This "download a chunk, upload that chunk, repeat" pattern means at
    most one chunk is ever held in memory at a time - neither the full
    source artifact nor the full re-uploaded data needs to fit in memory
    or on local disk - while still producing exactly ONE resulting
    artifact (not one artifact per chunk). This is useful for
    exercising/testing the handling of artifacts too large to buffer or
    store locally: lower 'chunk_size_bytes' for many small round trips
    against a test artifact, or raise it for a genuinely huge artifact.

    Note: streaming the upload this way requires the source artifact's
    total size to be known upfront (the TUS protocol needs the total
    'Upload-Length' when the session is created). If the size is unknown,
    this falls back to buffering the full download in memory before doing
    a single, regular (non-chunked) upload.

    :param req: ArtifactTester object containing the artifact urn, upload
        flag, and chunk size.
    :return: an ArtifactResult describing the downloaded artifact and, if
        uploaded, the resulting (single) artifact urn.
    """
    ivcap = ctxt.ivcap
    # 'chunk_size_bytes' is Optional, so an explicit 'null' in the request
    # would otherwise bypass the Pydantic field default - fall back here too.
    chunk_size = req.chunk_size_bytes or DEFAULT_ARTIFACT_CHUNK_SIZE_BYTES

    artifact = ivcap.get_artifact(req.artifact_urn)

    downloaded_bytes = 0
    chunk_count = 0
    uploaded_artifact_urn: str | None = None

    with ctxt.report.step(
        "download_upload_artifact",
        f"Downloading artifact {req.artifact_urn} in {chunk_size}-byte chunks"
        + (" and streaming them into a new artifact" if req.upload_also else ""),
        artifact_urn=req.artifact_urn,
        chunk_size_bytes=chunk_size,
        upload_also=req.upload_also,
    ) as step:
        # as_stream(chunk_size=...) performs a streaming HTTP GET and yields
        # exactly 'chunk_size'-sized byte chunks (the last one may be
        # smaller), so only one chunk is ever buffered by the HTTP client
        # at a time.
        source_chunks = artifact.as_stream(chunk_size=chunk_size)

        def tracked_chunks() -> Iterator[bytes]:
            nonlocal downloaded_bytes, chunk_count
            for chunk in source_chunks:
                chunk_count += 1
                downloaded_bytes += len(chunk)
                step.info(
                    event={
                        "chunk": chunk_count,
                        "chunk_bytes": len(chunk),
                        "downloaded_bytes": downloaded_bytes,
                    }
                )
                yield chunk

        if req.upload_also and artifact.size and artifact.size > 0:
            # Wrap the chunk iterator in a sequential-read adapter and hand
            # it straight to upload_artifact() as a single streamed upload:
            # each chunk is appended (via one TUS PATCH request) directly
            # onto the single resulting artifact as soon as it is
            # downloaded - no full buffering, and exactly one artifact is
            # created.
            stream = _SequentialReadStream(tracked_chunks(), artifact.size)
            uploaded = ivcap.upload_artifact(
                name=artifact.name or "uploaded-artifact",
                io_stream=cast(IO[bytes], stream),
                content_type=artifact.mime_type or "application/octet-stream",
                content_size=artifact.size,
                chunk_size=chunk_size,
            )
            uploaded_artifact_urn = uploaded.id
        elif req.upload_also:
            # Source artifact size is unknown, so a streamed single-pass
            # TUS upload isn't possible (Upload-Length must be known up
            # front). Fall back to buffering the chunks fully in memory
            # before doing one regular upload.
            buffer = io.BytesIO()
            for chunk in tracked_chunks():
                buffer.write(chunk)
            buffer.seek(0)
            uploaded = ivcap.upload_artifact(
                name=artifact.name or "uploaded-artifact",
                io_stream=buffer,
                content_type=artifact.mime_type or "application/octet-stream",
                content_size=downloaded_bytes,
            )
            uploaded_artifact_urn = uploaded.id
        else:
            for _ in tracked_chunks():
                pass

        step.finished(
            msg=f"Downloaded {downloaded_bytes} bytes in {chunk_count} chunks",
            downloaded_bytes=downloaded_bytes,
            chunk_count=chunk_count,
        )

    return ArtifactResult(
        artifact_urn=artifact.id,
        name=artifact.name,
        mime_type=artifact.mime_type,
        downloaded_bytes=downloaded_bytes,
        chunk_count=chunk_count,
        chunk_size_bytes=chunk_size,
        uploaded_artifact_urn=uploaded_artifact_urn if req.upload_also else None,
    )
