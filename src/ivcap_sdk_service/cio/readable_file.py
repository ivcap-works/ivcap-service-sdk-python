#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
from builtins import BaseException
from typing import IO, AnyStr, Callable, List, Optional
import filetype
import io

from ..logger import sys_logger as logger

from .io_adapter import IOReadable


class ReadableFile(IOReadable):
    """
    A class representing a readable file.

    Attributes:
        _name (str): The name of the file.
        _path (Optional[str]): The path to the file.
        _file_obj (IO[bytes]): The file object.
        _on_close (Optional[Callable[[IO[bytes]], None]]): A callback function to be called when the file is closed.
        _closed (bool): A flag indicating whether the file is closed.
    """

    def __init__(
        self,
        name: str,
        path: Optional[str],
        on_close: Callable[[IO[bytes]], None] = None,
        is_binary=True,
        encoding=None,
    ):
        self._name = name
        self._path = path
        self._mode = "rb" if is_binary else "r"
        self._file_obj = io.open(path, mode=self._mode, encoding=encoding)
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

    @property
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
            logger.warning(
                "ReadableProxyFile#close: on_close '%s' failed with '%s'",
                self._on_close,
                err,
            )
        finally:
            f.close()

    def __repr__(self):
        return (
            f"<ReadableFile name={self._name} closed={self._closed} path={self._path}>"
        )

    def to_json(self):
        """
        Returns the name of the readable file as a JSON string.

        :return: A JSON string representing the name of the readable file.
        :rtype: str
        """
        return self._name
