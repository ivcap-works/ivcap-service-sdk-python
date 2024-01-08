#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
"""
FileAdapter a thin wrapper around io.IOBase that sets a storage path with
standard filesystem backend
"""
import glob
import json
import os
from pathlib import Path, PurePath
import pathlib
import shutil
from typing import Optional, Union
from os import access, R_OK
from os.path import isfile, join
from urllib.parse import urlparse
import time
from filelock import FileLock


from .readable_file import ReadableFile

from .readable_proxy import ReadableProxy
from .writable_file import WritableFile

from .utils import get_cache_name
from ..utils import json_dump
from ..itypes import URN, MetaDict, Url, SupportedMimeTypes



from ..logger import sys_logger as logger
from .io_adapter import DEF_LEASE_TIME_SEC, END_OF_STREAM_SCHEMA, AcknowledgableQueueMessage, Collection, IOAdapter, IOReadable, IOWritable, OnCloseF, Queue, QueueMessage

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

    def _to_path(self, prefix: str, name: str, collection_name: str = None, ext = None) -> str:

        if name.startswith('/'):
            path = name
        elif name.startswith('file:'):
            path = name[len('file://'):]
        elif name.startswith('urn:file:'):
            path = name[len('urn:file://'):]
        else:
            if collection_name:
                path = os.path.join(prefix, collection_name, name)
            else:
                path = os.path.join(prefix, name)
        if ext:
            path = PurePath(path).with_suffix(f".{ext}").as_posix()
                
        return path

    def write_metadata(
        self,
        entity_id: str, # URN
        schema: str, # URN
        metadata: MetaDict,
        name: Optional[str] = None,
    ) -> str:
        if entity_id == 'urn:ivcap:order:00000000-0000-0000-0000-000000000000':
            # debug mode
            if name:
                fn = f"{name}.{time.time()}.json"
            else:
                fn = f"{schema}.{time.time()}.json"
            e = os.path.basename(fn)
        else:
            if name:
                fn = f"urn:ivcap:aspect#{name}.json"
            else:
                fn = f"urn:ivcap:aspect#{entity_id}--{schema}.json"
            e = os.path.basename(fn)
            if not e.startswith("urn"):
                e = f"urn:{e}"
        fname = self._to_path(self.out_dir, e)
        json_dump(metadata, fname)
        return e
                              
    def read_aspect(self, aspect_urn: URN, no_caching=False) -> dict:
        """Return an aspect as a dict

        Args:
            aspect_urn (URN): URN of aspect to read
            no_caching (bool, optional): If true, content is not cached nor read from cache. Defaults to False.

        Returns:
            dict: The content of the aspect as a dict
        """
        fname = self._to_path(self.out_dir, aspect_urn, ext="json")
        if os.path.isfile(fname):
            with open(fname) as f:
                a = json.load(f)
                return a
        else:
            raise ValueError(f"Cannot find local file for aspect '{fname}")
                                   
    def get_collection(self, collection_urn: str) -> Collection:
        u = urlparse(collection_urn)
        if u.scheme == '' or u.scheme == 'file':
            if os.path.isfile(u.path) or os.path.isdir(u.path):
                return LocalCollection(u.path, self)
            else:
                raise ValueError(f"Cannot find local file or directory '{u.path}")
        else:
            raise ValueError(f"Remote collection is not supported, yet")

    def get_queue(self, queue_urn: str) -> Queue:
        return LocalQueue(queue_urn, self)
    
    def __repr__(self):
        return f"<LocalIOAdapter in_dir={self.in_dir} out_dir={self.out_dir}>"

class LocalCollection(Collection):
    def __init__(self, path: str, adapter: IOAdapter) -> None:
        super().__init__()
        self._path = path
        self._adapter = adapter
    
    @property
    def name(self) -> str:
        return os.path.basename(self._path)

    @property
    def urn(self) -> str:
        return f"urn:file://{self._path}"
    
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

### QUEUE

class LocalQueueMessage(AcknowledgableQueueMessage): 
    pending: str = None
    
    def ack(self) -> None:
        if self.pending:
            pathlib.Path(self.pending).unlink(missing_ok=True)
            
 
    
class LocalQueue(Queue):
    """A queue of messages"""
    
    def __init__(self, urn: str, adapter: LocalIOAdapter) -> None:
        from ..config import Resource
        from ..ivcap import get_config # break import loop
        
        self._urn = urn
        self._path = resource_urn_path(urn, Resource.QUEUE, adapter.in_dir)
        self._pending_path = os.path.join(self._path, "_pending")
        if not os.path.isdir(self._pending_path):
            os.mkdir(self._pending_path)
        
        self._name = Path(self._path).stem
        self._id_prefix = f"{get_config().SCHEMA_PREFIX}{Resource.MESSAGE.value}#{self._name}-"
        self._lock_file = os.path.join(self._path, "_queue.lock")
        self._msg_glob = os.path.join(self._path, "*.json")
        self._adapter = adapter
        
    @property
    def name(self) -> str:
        return self._name

    @property
    def urn(self) -> str:
        return self._urn

    def push(self, m: QueueMessage) -> URN:
        with FileLock(self._lock_file):
            h = self._get_msg_index(highest=True)
            n = 1 if not h else h + 1
            fn = "{:08d}.json".format(n)
            with open(os.path.join(self._path, fn), "w") as f:
                m.id = f"{self._id_prefix}{n}"
                f.write(m.to_json(indent=2))

    def pull(self, lease=DEF_LEASE_TIME_SEC) -> AcknowledgableQueueMessage:
       with FileLock(self._lock_file):
            n = self._get_msg_index(highest=False)
            if not n:
                # no more messages, lets return DONE message 
                return LocalQueueMessage(schema=END_OF_STREAM_SCHEMA, content={})
            
            fn = "{:08d}.json".format(n)
            mpath = os.path.join(self._path, fn)
            with open(mpath, "r") as f:
                s = f.read()
                m = LocalQueueMessage.from_json(s)
                # make pending
                pfn = f"{int(time.time()) + lease}--{fn}"
                ppath = os.path.join(self._pending_path, pfn)
                shutil.move(mpath, ppath)
                m.pending = ppath
                return m
    
    def _get_msg_index(self, highest: bool) -> Union[int, None]:
        fl = sorted(filter(os.path.isfile, glob.glob(self._msg_glob)), reverse=highest)
        if len(fl) == 0:
            return None
        p = fl[0]
        s = Path(p).stem
        return int(s)
    
    def __iter__(self):
        return QueueIter(self)

    def __repr__(self):
        return f"<LocalQueue path={self._path}>"

class QueueIter:
    def __init__(self, queue: LocalQueue) -> None:
        self._queue = queue
        self._last_msg = None
        
    def __next__(self):
        if self._last_msg:
            # assume previious message is processed
            self._last_msg.ack()
        m = self._queue.pull()
        if m.schema == END_OF_STREAM_SCHEMA:
            self._last_msg = None
            raise StopIteration

        self._last_msg = m
        return m


def resource_urn_path(urn: str, resource: str, in_dir: str) -> str:
    """Returns the 'path' of a resource urn (eveything after ':' or '#')"""

    u = urlparse(urn)
    if u.scheme == '' or u.scheme == 'file':
        path = u.path
    elif u.scheme == 'urn':
        from ..ivcap import get_config # break import loop

        if u.fragment != "":
            dname = u.fragment
        else:
            prefix = f"{get_config().SCHEMA_PREFIX}{resource.value}:"
            dname = u.path[len(prefix)]
        path = os.path.join(in_dir, dname)
        if not os.path.isdir(path):
            path = os.path.join(get_config().OUT_DIR, dname)
            os.mkdir(path)
    else:
        raise ValueError(f"Cannot map '{urn}' to a local resource")

    if os.path.isdir(path):
        return path
    else:
        raise ValueError(f"Cannot find local file or directory '{path}")
