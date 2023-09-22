#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
"""
FileAdapter a thin wrapper around io.IOBase that sets a storage path with
standard filesystem backend
"""
import os
from pathlib import Path
from typing import Optional
from os import access, R_OK
from os.path import isfile, join
from urllib.parse import urlparse
import time

from .readable_file import ReadableFile

from .readable_proxy import ReadableProxy
from .writable_file import WritableFile

from .utils import get_cache_name
from ..utils import json_dump
from ..itypes import MetaDict, Url, SupportedMimeTypes

from ..logger import sys_logger as logger
from .io_adapter import Collection, IOAdapter, IOReadable, IOWritable, OnCloseF

class LocalIOAdapter(IOAdapter):
    """
    An adapter for a standard file system backend.
    """
    def __init__(self, in_dir: str, out_dir: str, cache_dir: str=None) -> None:
        """
        Initialise FileAdapter data paths

        Parameters
        ----------
        order_id: str
            Id of order from API
        in_dir: str
            Path of input data
        out_dir: str
            Path of output data

        Returns
        -------
        None

        """
        super().__init__()
        self.in_dir = os.path.abspath(in_dir)
        self.out_dir = os.path.abspath(out_dir)
        self.cache_dir = os.path.abspath(cache_dir) if cache_dir else None

    def read_artifact(self, artifact_id: str, binary_content=True, no_caching=False, seekable=False) -> IOReadable:
        """Return a readable file-like object providing the content of an artifact

        Args:
            artifact_id (str): ID of artifact to read
            binary_content (bool, optional): If true content is expected to be of binary format otherwise text is expected. Defaults to True.
            no_caching (bool, optional): If true, content is not cached nor read from cache. Defaults to False.
            seekable (bool, optional): If true, returned readable should be seekable

        Returns:
            IOReadable: The content of the artifact as a file-like object
        """
        u = urlparse(artifact_id)
        if u.scheme == '' or u.scheme == 'file':
            return self.read_local(u.path, binary_content=binary_content)
        else:
            return self.read_external(artifact_id, binary_content=binary_content, no_caching=no_caching, seekable=seekable)

    def read_external(self, 
        url: Url, 
        binary_content=True, 
        no_caching=False, 
        seekable=False,
        local_file_name=None
    ) -> IOReadable:
        """Return a readable file-like object providing the content of an external data item.

        Args:
            url (Url): URL of external object to read
            binary_content (bool, optional): If true content is expected to be of binary format otherwise text is expected. Defaults to True.
            no_caching (bool, optional): If set, content is not cached nor read from cache. Defaults to False.
            seekable (bool, optional): If true, returned readable should be seekable

        Returns:
            IOReadable: The content of the external data item as a file-like object
        """
        cache = None
        if self.cache_dir and not no_caching:
            cname = local_file_name if local_file_name else join(self.cache_dir, get_cache_name(url))
            if isfile(cname) and access(cname, R_OK):
                return ReadableFile(f"{url} (cached)", cname, is_binary=binary_content)
            cache = WritableFile(cname, is_binary=binary_content)

        ior = ReadableProxy(url, url, is_binary=binary_content, cache=cache)
        if cache:
            logger.debug("LocalIOAdapter#read_external: Cache external content '%s' into '%s'", url, cache.name)
        return ior

    def artifact_readable(self, artifact_id: str) -> bool:
        """Return true if artifact exists and is readable

        Args:
            artifact_id (str): ID of artifact

        Returns:
            bool: True if artifact can be read
        """
        u = urlparse(artifact_id)
        if u.scheme == '' or u.scheme == 'file':
            return self.readable_local(u.path)
        else:
            return True # assume that all external urls are at least conceptually readable
    
    def write_artifact(
        self,
        mime_type: str, 
        *,
        name: Optional[str] = None,
        metadata: Optional[MetaDict] = {}, 
        seekable=False,
        on_close: Optional[OnCloseF] = None
    ) -> IOWritable:
        """Returns a IOWritable to create a new artifact. It needs to be closed
        in order to be persisted. If `on_close` is provided it is called with the 
        artifactID.

        Args:
            mime_type (str): _description_
            name (Optional[str], optional): Optional name. Defaults to None.
            collection_name (Optional[str], optional): Optional collection name. Defaults to None.
            metadata (Optional[MetaDict], optional): Key/value pairs to add as metadata. Defaults to {}.
            seekable (bool, optional): If true, writable should be seekable (needed for NetCDF). Defaults to False.
            on_close (Optional[OnCloseF], optional): Called with assigned artifact ID. Defaults to None.

        Returns:
            IOWritable: A file-like object to write deliver artifact content - needs to be closed
        """
        fname = self._to_path(self.out_dir, name)
        if isinstance(mime_type, SupportedMimeTypes):
            mime_type = mime_type.value
        is_binary = not mime_type.startswith('text')

        def _on_close(urn, _2):
            logger.info("Written artifact '%s' to '%s'", name, fname)
            if metadata != {}:
                json_dump(metadata, f"{fname}-meta.json")
            if on_close:
                on_close(urn)

        return WritableFile(fname, _on_close, is_binary, use_temp_file=False)

    def readable_local(self, name: str, collection_name: str = None) -> bool:
        """Return true if file exists and is readable. If 'name' starts with a '/'
        it is assumed to be an absolute path. If not, it's assumed to be local to self._in_dir

        Args:
            name (str): Name of file or path to it when it starts with '/'
            collection_name (str, optional): Optional collection name which would create local directory. Defaults to None.

        Returns:
            bool: True if file is readable
        """
        file_name = self._to_path(self.in_dir, name, collection_name)
        return isfile(file_name) and access(file_name, R_OK)

    def read_local(self, name: str, collection_name: str = None, binary_content=True) -> IOReadable:
        """Return a readable file-like object providing the content of an external data item.

        Args:
            name (str): Name of file or path to it when it starts with '/'
            collection_name (str, optional): Optional collection name which would create local directory. Defaults to None.
            binary_content (bool, optional): If true content is expected to be of binary format otherwise text is expected. Defaults to True.

        Returns:
            IOReadable: The content of the local file as a file-like object
        """
        path = self._to_path(self.in_dir, name, collection_name)
        name = os.path.basename(path)
        return ReadableFile(name, path, is_binary=binary_content)

    def _to_path(self, prefix: str, name: str, collection_name: str = None) -> str:
        if name.startswith('/'):
            return name
        elif name.startswith('file:'):
            return name[len('file://'):]
        elif name.startswith('urn:file:'):
            return name[len('urn:file://'):]
        else:
            if collection_name:
                return os.path.join(prefix, collection_name, name)
            else:
                return os.path.join(prefix, name)

    def write_metadata(
        self,
        entity_id: str, # URN
        schema: str, # URN
        metadata: MetaDict,
    ) -> str:
        if entity_id == 'urn:ivcap:order:00000000-0000-0000-0000-000000000000':
            # debug mode
            e = os.path.basename(f"{schema}.{time.time()}.json")
        else:
            e = os.path.basename(f"{entity_id}:{schema}.json")
            if not e.startswith("urn"):
                e = f"urn:{e}"
        fname = self._to_path(self.out_dir, e)
        json_dump(metadata, fname)
        return e
                              
                                   
    def get_collection(self, collection_urn: str) -> Collection:
        u = urlparse(collection_urn)
        if u.scheme == '' or u.scheme == 'file':
            if os.path.isfile(u.path) or os.path.isdir(u.path):
                return LocalCollection(u.path, self)
            else:
                raise ValueError(f"Cannot find local file or directory '{u.path}")
        else:
            raise ValueError(f"Remote collection is not supported, yet")
        
    def __repr__(self):
        return f"<LocalIOAdapter in_dir={self.in_dir} out_dir={self.out_dir}>"

class LocalCollection(Collection):
    def __init__(self, path: str, adapter: IOAdapter) -> None:
        super().__init__()
        self._path = path
        self._adapter = adapter
        
    def name(self) -> str:
        return self._collection_urn
    
    def __iter__(self):
        if os.path.isfile(self._path):
            return SingleFileIter(self._path, self._adapter)
        else:
            return DirectoryIter(self._path, self._adapter)

    def __repr__(self):
        return f"<LocalCollection path={self._path}>"

class SingleFileIter:
    def __init__(self, path: str, adapter: IOAdapter) -> None:
        self._path = path
        self._adapter = adapter
        self._already_served = False
        
    def __next__(self):
        if self._already_served:
            raise StopIteration
        else:
            self._already_served = True
            return self._adapter.read_local(self._path)

    def __repr__(self):
        return f"<LocalCollectionIter path={self._path}>"

class DirectoryIter:
    def __init__(self, path: str, adapter: IOAdapter) -> None:
        self._iter = Path(path).glob('*')
        self._adapter = adapter
        self._already_served = False
        
    def __next__(self):
        f = str(next(self._iter))
        return self._adapter.read_local(f)
