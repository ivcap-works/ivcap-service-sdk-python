#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
from builtins import BaseException
from typing import IO, AnyStr, Callable, List, Optional
import tempfile
import io

from ivcap_sdk_service.cio.utils import download
from ..logger import sys_logger as logger

from .io_adapter import IOReadable, IOWritable

class ReadableProxy(IOReadable):

    def __init__(self, 
        url: str,
        name=None,
        on_close: Callable[[IO[bytes]], None]=None, 
        is_binary=True, 
        encoding=None,
        cache: Optional[IOWritable] = None
    ):
        self._name = name if name else url
        self._is_binary = is_binary
        self._mode = "rb" if is_binary else "r"
        self._download_url = url
        self._encoding = encoding
        self._on_close = on_close
        self._cache = cache
        self._offset = 0
        self._file_obj = None
        self._closed = False
    
    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def name(self) -> str:
        return self._name

    def as_local_file(self) -> str:
        self._get_file_obj()
        return self._path

    def writable(self) -> bool:
        return self._writable_also

    def readable(self) -> bool:
        return True
    
    def readline(self, limit: int = -1) -> AnyStr:
        raise Exception("not implemented")

    def readlines(self, hint: int = -1) -> List[AnyStr]:
        raise Exception("not implemented")


    def seek(self, offset, whence=io.SEEK_SET):
        """
        Change stream position by offset
        """
        # if whence == io.SEEK_SET:
        #     self._offset = offset
        # elif whence == io.SEEK_CUR:
        #     self._offset += offset
        # else:
        #     raise OSError(-1, "cannot seek from end")
        self._get_file_obj().seek(offset, whence)
        if self._cache:
            self._cache.seek(offset, whence)

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        """
        Return current stream position
        """
        return self._get_file_obj().tell()

    def read(self, n: int = -1) -> AnyStr:
        s = self._get_file_obj().read(n)
        if self._cache:
            n = self._cache.write(s)
            if n != len(s):
                logger.warn("ReadableProxy#read: caching last read failed")
                try:
                    self._cache.close()
                except:
                    pass
                finally:
                    self._cache = None
        return s

    def close(self):
        self._closed = True
 
        if self._cache:
            try:
                self._cache.close()
            except:
                logger.warn("ReadableProxy#close: closing cache failed with '%s'", err)
            finally:
                self._cache = None


        f = self._get_file_obj()
        try:
            if self._on_close:
                self._on_close(f)
        except BaseException as err:
            logger.warn("ReadableProxyclose: on_close '%s' failed with '%s'", self._on_close, err)
        finally:
            f.close()
 

    def _get_file_obj(self):
        if self._file_obj == None:
            self._open_file_obj()
        return self._file_obj
    
    def _open_file_obj(self):
        """Open and ensure that the local file object is properly "filled".

        If the content is from an external source, ensure that it is fully
        downloaded into `_file_obj`.
        """

        if self._download_url:
            mode = "w+b" if self._is_binary else "w+"
            self._file_obj = tempfile.NamedTemporaryFile(mode, encoding=self._encoding)
            self._path = self._file_obj.name
            try:
                cacheID = download(self._download_url, self._file_obj, close_fhdl=False)
                if cacheID:
                    self._name = f"{self._name} ({cacheID})"
            except BaseException as ex:
                logger.error("ReadableProxy#_open_file_obj: While downloading - %s", ex.__repr__())
                raise ex
            
            logger.debug("ReadableProxy#_open_file_obj: Read external content '%s' into '%s'", self._download_url, self._path)

        elif self._path:
            self._file_obj = io.open(self._path, mode=self._mode, encoding=self._encoding)

    def __repr__(self):
        return f"<ReadableProxy name={self._name} closed={self._closed} mode={self._mode}>"

    def to_json(self):
        return self._name
