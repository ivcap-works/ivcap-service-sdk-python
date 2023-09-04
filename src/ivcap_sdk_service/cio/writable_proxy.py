#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
from builtins import BaseException
import collections
import sys
from typing import AnyStr, Callable, List, Optional, Sequence, Union
import tempfile
import io
import requests
from ivcap_sdk_service.cio.utils import encode64

from ivcap_sdk_service.itypes import MetaDict, SupportedMimeTypes
from ivcap_sdk_service.utils import json_dump
from ..logger import sys_logger as logger

from .io_adapter import IOWritable

class WritableProxy(IOWritable):
    """
    A class which implements the IOWritable interface for writing data. It additionally
    persists the data on disk.

    ...

    Args:
        name (str): _description_
        on_close (Callable[[IO[bytes], None]]): _description_. Defaults to None.
        is_binary (bool, optional): _description_. Defaults to True.
        use_temp_file (bool, optional): _description_. Defaults to True.
        encoding (_type_, optional): _description_. Defaults to None.
    """

    def __init__(self, 
        storage_url: str,
        mime_type: str, 
        metadata: Optional[Union[MetaDict, Sequence[MetaDict]]] = None,
        name: Optional[str] = None,
        is_seekable=False,
        on_close: Optional[Callable[[str, str], str]]=None, 
        encoding=None,
    ):
        self._storage_url = storage_url
        if isinstance(mime_type, SupportedMimeTypes):
            mime_type = mime_type.value
        is_binary = not mime_type.startswith('text')

        self._mime_type = mime_type
        self._name = name if name else "???"
        self._metadata = metadata

        # At this stage, we first write it to a local temp file and on close, post the file
        # to 'url'
        mode = "w+b" if is_binary else "w+"
        self._file_obj = tempfile.NamedTemporaryFile(mode, encoding=encoding) # delete after uploaded
        self.cnt = 0
        self._on_close = on_close
        self._closed = False

    @property
    def urn(self) -> str:
        return "???WHAT???"

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def name(self) -> str:
        return self._name

    def seek(self, offset, whence=io.SEEK_SET):
        """
        Change stream position by offset
        """
        diff = offset - self.cnt
        self.cnt += diff
        self._file_obj.seek(offset, whence)

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        """
        Return current stream position
        """
        stream_pos = self._file_obj.tell()
        return stream_pos

    def write(self, bytes_obj: AnyStr) -> int:
        bytes_written = self._file_obj.write(bytes_obj)
        self.cnt += bytes_written
        return bytes_written

    def writelines(self, lines: List[AnyStr]) -> None:
        self._file_obj.writelines(lines)

    def writable(self) -> bool:
        return True

    def truncate(self, size: int = None) -> int:
        self.cnt = self._file_obj.truncate(size)
        return self.cnt

    def readable(self) -> bool:
        return False

    def flush(self) -> None:
        self._file_obj.flush()

    def close(self):
        self._closed = True
        url = self._upload()
        try:
            if self._on_close:
                self._on_close(url, self._name)
        except BaseException as err:
            logger.warning("WritableProxy#close: on_close '%s' failed with '%s'", self._on_close, err)
        finally:
            self._file_obj.close()

    def _upload(
        self, 
    ) -> str:
        fd = self._file_obj
        logger.info("Upload artifact '%s'", self._name)
        fd.flush()
        fd.seek(0)

        metadata = self._metadata
        if metadata:
            if not isinstance(metadata, collections.Sequence):
                metadata = [metadata]
        else:
            metadata = []
        metadataUploaded = False

        # dataType = str(type(self.dataPeek))
        # ct = type2mime.get(dataType, "unknown")
        headers = {
            "Content-Type": self._mime_type,
        }
        if self._name:
            headers["X-Name"] = self._name

        if len(metadata) == 1 and len(metadata[0].keys()) <= 3:
            # Immediately upload simple metadata
            metadataUploaded = True
            headers['Upload-Metadata'] = ','. join(map(lambda e: f"{e[0]} {encode64(str(e[1]))}", metadata[0].items()))
        try:
            logger.debug("Post artifact data='%s', headers:'%s'", fd, headers)
            r = requests.post(self._storage_url, data=fd, headers=headers)
        except:
            print(">>>>", sys.exc_info())
            logger.fatal(f"while posting result data {self._storage_url} - {sys.exc_info()[0]}")
            sys.exit(-1)
        if r.status_code >= 300:
            logger.fatal(f"error response {r.status_code} while posting result data {self._storage_url}")
            sys.exit(-1)

        j = r.json()
        size = j['size']
        artifactID = j['id']
        if not artifactID:
            artifactID = r.headers.get('X-Artifact-Id')
        logger.info(f"WritableProxy: created artifact '{artifactID}' of size '{size}' via '{self._storage_url}'")

        if not metadataUploaded and len(metadata) > 0:
            url = r.headers.get('Location')
            for md in metadata:
                upload_metadata(self._storage_url, artifactID, md, artifact_id=artifactID, url=url)
        return artifactID

    # def _upload_metadata(
    #     self, 
    #     metadata: Sequence[MetaDict],
    #     artifactID: str,
    #     url: str,
    # ) -> None:
    #     for md in metadata:
    #         headers = {
    #             "X-Meta-Data-For-Url": url,
    #             "X-Meta-Data-For-Artifact": artifactID,
    #             "X-Meta-Data-Schema": md.get('$schema', '???'),
    #             "Content-Type": "application/json",
    #         }
    #         try:
    #             logger.debug("Post artifact metadata data='%s', headers:'%s'", md, headers)
    #             payload = json_dump(md)
    #             r = requests.post(self._storage_url, data=payload, headers=headers)
    #         except:
    #             logger.fatal(f"while posting metadata {self._storage_url} - {sys.exc_info()}")
    #             sys.exit(-1)
    #         if r.status_code >= 300:
    #             logger.fatal(f"error response {r.status_code} while posting metadata {self._storage_url}")
    #             sys.exit(-1)

    def __repr__(self):
        return f"<WritableProxy name={self._name} closed={self._closed} fp={self._file_obj}>"

def upload_metadata(
    storage_url: str,
    entity_urn: str,
    metadata: MetaDict,
    *,
    artifact_id: str = None,
    url: str = None,
) -> None:
    headers = {
        "X-Meta-Data-For-Entity": entity_urn,
        "X-Meta-Data-Schema": metadata.get('$schema', '???'),
        "Content-Type": "application/json",
    }
    if artifact_id:
        headers["X-Meta-Data-For-Artifact"] = artifact_id
    if url:
        headers["X-Meta-Data-For-Url"] = url

    try:
        logger.debug("Post artifact metadata data='%s', headers:'%s'", metadata, headers)
        payload = json_dump(metadata)
        r = requests.post(storage_url, data=payload, headers=headers)
    except:
        logger.fatal(f"while posting metadata {storage_url} - {sys.exc_info()}")
        sys.exit(-1)
    if r.status_code >= 300:
        logger.fatal(f"error response {r.status_code} while posting metadata {storage_url}")
        sys.exit(-1)
