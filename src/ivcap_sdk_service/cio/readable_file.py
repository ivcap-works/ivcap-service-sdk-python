#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
from builtins import BaseException
from typing import IO, AnyStr, Callable, List, Optional
import filetype
import io

from ivcap_sdk_service.cio.utils import download
from ..logger import sys_logger as logger

from .io_adapter import IOReadable

class ReadableFile(IOReadable):

    def __init__(self, 
        name: str,
        path: Optional[str],
        on_close: Callable[[IO[bytes]], None]=None, 
        is_binary=True,
        encoding=None,
    ):
        self._name = name
        self._path = path
        mode = "rb" if is_binary else "r"
        self._file_obj = io.open(path, mode=mode, encoding=encoding)
        self._on_close = on_close
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def urn(self) -> str:
        return f"urn:file://{self._path}"

    @property
    def name(self) -> str:
        return self._name
    
    @property
    def mime_type(self) -> str:
        kind = filetype.guess(self._path)
        if kind is None:
            return "unknown"
        else:
            return kind.mime

    def as_local_file(self) -> str:
        return self._path

    def writable(self) -> bool:
        return False

    def readable(self) -> bool:
        return True

    def seek(self, offset, whence=io.SEEK_SET):
        """
        Change stream position by offset
        """
        self._file_obj.seek(offset, whence)

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        """
        Return current stream position
        """
        return self._file_obj.tell()

    def read(self, n: int = -1) -> AnyStr:
        return self._file_obj.read(n)

    def readline(self, limit: int = -1) -> AnyStr:
        return self._file_obj.readline(limit)

    def readlines(self, hint: int = -1) -> List[AnyStr]:
        return self._file_obj.readlines(hint)

    def close(self):
        self._closed = True
        f = self._file_obj
        try:
            if self._on_close:
                self._on_close(f)
        except BaseException as err:
            logger.warn("ReadableProxyFile#close: on_close '%s' failed with '%s'", self._on_close, err)
        finally:
            f.close()

    def __repr__(self):
        return f"<ReadableFile name={self._name} closed={self._closed} path={self._path}>"

    def to_json(self):
        return self._name
