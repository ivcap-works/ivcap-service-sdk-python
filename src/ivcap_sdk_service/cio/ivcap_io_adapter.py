#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
"""
Implementation of the IOAdapter class for use inside the IVCAP platform
"""
import os
from typing import Callable, Optional, Sequence, Union
from os import access, R_OK
from os.path import isfile
from urllib.parse import urlparse

from .readable_file import ReadableFile
from .readable_proxy import ReadableProxy
from ..itypes import MetaDict, Url

from .io_adapter import Collection, IOAdapter, IOReadable, IOWritable, OnCloseF
from .writable_proxy import WritableProxy

class IvcapIOAdapter(IOAdapter):
    """
    An adapter for operating inside an IVCAP container.
    """
    def __init__(self, 
        storage_url: Url, 
        in_dir: str, 
        out_dir: str, 
        order_id:str, 
        cachable_url: Callable[[str], str],
    ) -> None:
        super().__init__()
        self.in_dir = os.path.abspath(in_dir)
        self.out_dir = os.path.abspath(out_dir)
        self.storage_url = storage_url
        self.cachable_url = cachable_url

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
        if artifact_id.startswith("urn:http"):
            # this is ectually an external link disguised as an artifact type (which it actually is)
            url = artifact_id[4:]
            return self.read_external(url, binary_content, no_caching, seekable)
        
        curl = self.cachable_url(artifact_id)
        ior = ReadableProxy(curl, name=artifact_id, is_binary=binary_content)
        return ior

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
        if no_caching:
            curl = url
        else:
            if url.startswith(self.storage_url):
                curl = url
            else:
                curl = self.cachable_url(url)
        ior = ReadableProxy(curl, name=url, is_binary=binary_content)
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
        name: Optional[str] = None,
        collection_name: Optional[str] = None,
        metadata: Optional[Union[MetaDict, Sequence[MetaDict]]] = None, 
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

        def _on_close(url, _):
            #url = self._upload_artifact(fd, mime_type, name, collection_name, metadata)
            if on_close:
                on_close(url)

        return WritableProxy(self.storage_url, mime_type, metadata, name, on_close=_on_close)

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
        return ReadableFile(name, path, None, is_binary=binary_content, use_temp_file=False)

    def _to_path(self, prefix: str, name: str, collection_name: str = None) -> str:
        if name.startswith('/'):
            return name
        elif name.startswith('file:'):
            return name[len('file://'):]
        else:
            if collection_name:
                return os.path.join(prefix, collection_name, name)
            else:
                return os.path.join(prefix, name)

    def get_collection(self, collection_urn: str) -> Collection:
        return IvcapCollection(collection_urn)

    def __repr__(self):
        return f"<IvcapIOAdapter in_dir={self.in_dir} out_dir={self.out_dir}>"

class IvcapCollection(Collection):
    def __init__(self, collection_urn: str) -> None:
        super().__init__()
        self._collection_urn = collection_urn
