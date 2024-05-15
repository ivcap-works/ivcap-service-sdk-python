#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
"""
FileAdapter a thin wrapper around io.IOBase that sets a storage path with
standard filesystem backend
"""
from enum import Enum
import fnmatch
import glob
import json
import os
from pathlib import Path, PurePath
import pathlib
from queue import Empty, SimpleQueue, Queue as StdQueue
import re
import shutil
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union
from os import access, R_OK, walk
from os.path import isfile, join
from urllib.parse import urlparse
import time
from filelock import FileLock
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import random
from jsonpath_ng import JSONPath
from jsonpath_ng.ext import parse as jp_parse

from .readable_file import ReadableFile
from .readable_proxy import ReadableProxy
from .writable_file import WritableFile
from .utils import get_cache_name
from ..utils import json_dump
from ..itypes import URN, AspectDict, MetaDict, Url, SupportedMimeTypes
from ..logger import sys_logger as logger
from .io_adapter import (
    A,
    ASPECT_MSG_SCHEMA,
    DEF_LEASE_TIME_SEC,
    DEF_MAX_WAIT_TIME_SEC,
    END_OF_STREAM_SCHEMA,
    AcknowledgableQueueMessage,
    Collection,
    IOAdapter,
    IOReadable,
    IOWritable,
    OnCloseF,
    Queue,
    QueueMessage,
    QueueTimeoutException,
    UnexpectedMessgeException,
    QueueService,
)
from ..aspect import Aspect, GenericAspect


class LocalIOAdapter(IOAdapter):
    """
    An adapter for a standard file system backend.
    """

    def __init__(self, in_dir: str, out_dir: str, cache_dir: str = None) -> None:
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

    def read_artifact(
        self, artifact_id: str, binary_content=True, no_caching=False, seekable=False
    ) -> IOReadable:
        """Return a readable file-like object providing the content of an artifact

        Args:
            artifact_id (str): ID of artifact to read
            binary_content (bool, optional): If true content is expected to be of binary format otherwise text is expected. Defaults to True.
            no_caching (bool, optional): If true, content is not cached nor read from cache. Defaults to False.
            seekable (bool, optional): If true, returned readable should be seekable

        Returns:
            IOReadable: The content of the artifact as a file-like object
        """
        if artifact_id.startswith("urn:"):
            artifact_id = artifact_id[4:]
        u = urlparse(artifact_id)
        if u.scheme == "" or u.scheme == "file":
            return self.read_local(u.path, binary_content=binary_content)
        else:
            return self.read_external(
                artifact_id,
                binary_content=binary_content,
                no_caching=no_caching,
                seekable=seekable,
            )

    def read_external(
        self,
        url: Url,
        binary_content=True,
        no_caching=False,
        seekable=False,
        local_file_name=None,
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
            cname = (
                local_file_name
                if local_file_name
                else join(self.cache_dir, get_cache_name(url))
            )
            if isfile(cname) and access(cname, R_OK):
                return ReadableFile(f"{url} (cached)", cname, is_binary=binary_content)
            cache = WritableFile(cname, is_binary=binary_content)

        ior = ReadableProxy(url, url, is_binary=binary_content, cache=cache)
        if cache:
            logger.debug(
                "LocalIOAdapter#read_external: Cache external content '%s' into '%s'",
                url,
                cache.name,
            )
        return ior

    def artifact_readable(self, artifact_id: str) -> bool:
        """Return true if artifact exists and is readable

        Args:
            artifact_id (str): ID of artifact

        Returns:
            bool: True if artifact can be read
        """
        u = urlparse(artifact_id)
        if u.scheme == "" or u.scheme == "file":
            return self.readable_local(u.path)
        else:
            return (
                True  # assume that all external urls are at least conceptually readable
            )

    def write_artifact(
        self,
        mime_type: str,
        *,
        name: Optional[str] = None,
        metadata: Optional[MetaDict] = {},
        seekable=False,
        is_binary: Optional[bool] = None,
        on_close: Optional[OnCloseF] = None,
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
        fname = self._to_path(self.out_dir, name, ensure_uniqueness=True)
        # if os.path.exists(fname):
        #     p = pathlib.Path(name)
        #     r = "{:05d}".format(random.randint(0,99999))
        #     n = f"{p.stem}-{r}{p.suffix}"
        #     fname = self._to_path(self.out_dir, n)
        if isinstance(mime_type, SupportedMimeTypes):
            mime_type = mime_type.value
        if is_binary == None:
            is_binary = not mime_type.startswith("text")

        def _on_close(urn, _2):
            logger.info("Written artifact '%s' to '%s'", name, fname)
            if metadata and metadata != {}:
                json_dump(metadata, f"{fname}-meta.json", entity=urn)
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

    def read_local(
        self, name: str, collection_name: str = None, binary_content=True
    ) -> IOReadable:
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

    def _to_path(
        self,
        prefix: str,
        name: str,
        collection_name: str = None,
        ext=None,
        ensure_uniqueness: bool = False,
    ) -> str:
        if name.startswith("/"):
            path = name
        elif name.startswith("file:"):
            path = name[len("file://") :]
        elif name.startswith("urn:file:"):
            path = name[len("urn:file://") :]
        else:
            if collection_name:
                path = os.path.join(prefix, collection_name, name)
            else:
                path = os.path.join(prefix, name)
        if ext:
            path = PurePath(path).with_suffix(f".{ext}").as_posix()

        if ensure_uniqueness and os.path.exists(path):
            p = pathlib.Path(path)
            r = "{:05d}".format(random.randint(0, 99999))
            n = f"{p.stem}-{r}{p.suffix}"
            path = self._to_path(self.out_dir, n)
        return path

    def write_metadata(
        self,
        entity_id: str,  # URN
        schema: str,  # URN
        metadata: MetaDict,
        name: Optional[str] = None,
    ) -> str:
        if entity_id == "urn:ivcap:order:00000000-0000-0000-0000-000000000000":
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
        fname = self._to_path(self.out_dir, e, ensure_uniqueness=True)
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

    def find_aspect(
        self,
        schema: URN = None,
        entity: URN = None,
        json_path: str = None,
        schema2type: Dict[str, Type[A]] = None,
    ) -> List[Aspect]:
        expr = self._create_jsonpath(json_path) if json_path else None
        results = []
        for fn in Path(self.out_dir).glob("*.json"):
            with open(fn) as f:
                aj = json.load(f)
                if not aj:
                    logger.warning(f"can't parse json in '{fn}'")
                    continue
                aschema = aj.get("$schema")
                if not aschema:
                    logger.warning(f"aspect does not have '$schema' - {fn}")
                    continue

                if schema and aschema != schema:
                    continue
                if entity:
                    aentity = aj.get("$entity")
                    if not aentity:
                        logger.warning(f"aspect does not have '$entity' - {fn}")
                        continue
                    if aentity != entity:
                        continue
                if expr:
                    m = expr.find([aj])
                    logger.debug(
                        f"checking json path in '{fn}' - matched: {len(m) == 1}"
                    )
                    if len(m) == 0:
                        continue
                klass = schema2type.get(aschema) if schema2type else None
                if klass:
                    a = klass(**aj)
                    aentity = aj.get("$entity")
                    if aentity:
                        a.ENTITY = aentity
                else:
                    a = GenericAspect(aschema, **aj)
                results.append(a)
        return results

    def _create_jsonpath(self, path: str = None) -> Optional[JSONPath]:
        if not path:
            return None

        if path.startswith("$"):
            # hope the caller knows what they are doing :)
            p = path
        elif path.startswith("@") or path.startswith("("):
            p = f"$[?{path}]"
        else:
            raise Exception("json_path should start with either '@' or '('")
        logger.debug(f"final json path '{p}'")
        return jp_parse(p)

    def get_collection(self, collection_urn: str) -> Collection:
        u = urlparse(collection_urn)
        if u.scheme == "" or u.scheme == "file":
            if os.path.isfile(u.path) or os.path.isdir(u.path):
                return LocalCollection(u.path, self)
            else:
                raise ValueError(f"Cannot find local file or directory '{u.path}")
        else:
            raise ValueError(f"Remote collection is not supported, yet")

    def get_queue_service(self, **kwargs) -> QueueService:
        return LocalQueueService(**kwargs)

    def get_queue(self, queue_urn: str) -> Queue:
        if queue_urn.startswith("urn:file:"):
            # for testing and debugging, we support a queue with a single file
            return TestQueue(queue_urn, self)
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
        self._iter = Path(path).glob("*")
        self._adapter = adapter
        self._already_served = False

    def __next__(self):
        f = str(next(self._iter))
        return self._adapter.read_local(f)


### QUEUE


class MsgState(str, Enum):
    Added = "A"
    Consumed = "C"
    Pending = "P"
    Timedout = "T"
    Released = "R"


class LocalQueueMessage(AcknowledgableQueueMessage):
    _pendingPath: str = None
    _origPath: str = None
    _queue: "LocalQueue" = None

    def ack(self) -> None:
        if self._pendingPath:
            with FileLock(self._queue._lock_file):
                pathlib.Path(self._origPath).unlink(missing_ok=True)
                pathlib.Path(self._pendingPath).unlink(missing_ok=True)
                self._queue._log(self._origPath, MsgState.Consumed)
                self._origPath = None
                self._pendingPath = None

    def release(self) -> None:
        """Release a message as not being processed and should be put back into the queue"""
        if self._pendingPath:
            with FileLock(self._queue._lock_file):
                if os.path.exists(self._pendingPath):
                    shutil.move(self._pendingPath, self._origPath)
                self._pendingPath = None
                self._queue._log(self._origPath, MsgState.Released)
                # with open(self._queue._log_file, "a") as f:
                #     f.write(f"{os.path.basename(self._origPath)},{MsgState.Released},{int(time.time())}\n")


EOS_LABEL = 99999999999

T = TypeVar("T")


class BaseQueue(Queue):
    def __init__(
        self,
        urn: str,
        adapter: LocalIOAdapter,
        lease: float = DEF_LEASE_TIME_SEC,
        timeout: float = DEF_MAX_WAIT_TIME_SEC,
    ) -> None:
        self._urn = urn
        self._name = urn[len("urn:ivcap:queue#")]
        self._adapter = adapter
        self._lease = lease
        self._timeout = timeout
        self._is_closed = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def urn(self) -> str:
        return self._urn

    @property
    def lease(self) -> float:
        return self._lease

    def withLease(self, lease: float) -> "Queue":
        q = self.__class__(self._urn, self._adapter, lease, self._timeout)
        q._is_closed = self._is_closed
        return q

    @property
    def timeout(self) -> float:
        return self._timeout

    def withTimeout(self, timeout: float) -> "Queue":
        q = self.__class__(self._urn, self._adapter, self._lease, timeout)
        q._is_closed = self._is_closed
        return q

    def close(self):
        self._is_closed = True

    def map(self, out_queue: Queue, mapper: Callable[[QueueMessage], QueueMessage]):
        count = 0
        while True:
            m = self.pull()
            if m.schema == END_OF_STREAM_SCHEMA:
                out_queue.push(m)
                m.ack()
                break
            else:
                outm = mapper(m)
                if outm:
                    if type(outm) in [list, tuple]:
                        for m2 in outm:
                            out_queue.push(m2)
                    else:
                        out_queue.push(outm)
                    m.ack()
                    count += 1
                else:
                    m.release()
        logger.info(f"done processing {count} message")

    def __iter__(self):
        return QueueIter(self)


class LocalQueue(BaseQueue):
    """A queue of messages"""

    def __init__(
        self,
        urn: str,
        adapter: LocalIOAdapter,
        lease: float = DEF_LEASE_TIME_SEC,
        timeout: float = DEF_MAX_WAIT_TIME_SEC,
    ) -> None:
        from ..config import Resource
        from ..ivcap import get_config  # break import loop

        super().__init__(urn, adapter, lease, timeout)
        self._path = resource_urn_path(urn, Resource.QUEUE, adapter.in_dir)
        self._pending_path = os.path.join(self._path, "_pending")
        self._idx_file = os.path.join(self._path, "_idx")
        self._log_file = os.path.join(self._path, "_log.csv")
        self._lock_file = os.path.join(self._path, "_queue.lock")
        with FileLock(self._lock_file):
            if not os.path.isdir(self._pending_path):
                os.mkdir(self._pending_path)
            if not os.path.exists(self._idx_file):
                with open(self._idx_file, "a") as f:
                    f.write("0")

        self._name = Path(self._path).stem
        self._id_prefix = (
            f"{get_config().SCHEMA_PREFIX}{Resource.MESSAGE.value}#{self._name}-"
        )
        self._idx_file = os.path.join(self._path, "_idx")
        self._msg_glob = os.path.join(self._path, "*.json")
        self._pending_glob = os.path.join(self._pending_path, "*.json")
        self._queue = None
        self._lock = Lock()
        self._observer = None

    def close(self):
        self._is_closed = True
        with self._lock:
            self._queue = None
            if self._observer:
                self._observer.stop()
                self._observer.join()
                self._observer = None
        # clean out pending - should only be EOS messages
        for f in glob.glob(os.path.join(self._pending_path, "*")):
            os.remove(f)
        logger.debug(f"Queue#{self._name} closed")

    def push(self, m: QueueMessage) -> URN:
        with FileLock(self._lock_file):
            n = self._get_next_msg_id()
            fn = "{:08d}.json".format(n)
            with open(os.path.join(self._path, fn), "w") as f:
                m.id = f"{self._id_prefix}{n}"
                logger.debug(f"Queue#{self._name} pushing message id '{n}'")
                f.write(m.to_json(indent=2))
            self._log(fn, MsgState.Added)
            # with open(self._log_file, "a") as f:
            #     f.write(f"{fn},{MsgState.Added},{int(time.time())}")

    def _get_next_msg_id(self):
        with open(self._idx_file, "r+") as f:
            c = f.read()
            n = int(c) + 1
            f.seek(0)
            f.write(f"{n}")
            f.flush()
            return n

    def pull(self) -> AcknowledgableQueueMessage:
        if self._is_closed:
            return LocalQueueMessage(schema=END_OF_STREAM_SCHEMA, content={})

        q = self._get_queue()
        abs_timeout = int(time.time()) + self._timeout
        block = False  # let's be optimisitc and assume there is a message waiting
        _timeout = 0
        while True:
            try:
                if _timeout:
                    logger.debug(
                        f"Queue#{self._name}: waiting for new messages - {_timeout}"
                    )
                p = q.get(block, _timeout)
                m = self._pull(p)
                if m:
                    if m.schema == END_OF_STREAM_SCHEMA:
                        self.close()
                    return m
            except Empty:
                # queue is empty, let's wait for new messages
                rem = abs_timeout - int(time.time())
                if rem <= 0:
                    raise QueueTimeoutException()
                block = True
                _timeout = self._calc_queue_timeout(rem)

    def _pull(self, mpath) -> AcknowledgableQueueMessage:
        with FileLock(self._lock_file):
            logger.debug(f"Queue#{self._name} checking for '{mpath}'")
            if not os.path.exists(mpath):
                return None
            fn = os.path.basename(mpath)
            logger.debug(f"Queue#{self._name} found '{fn}'")
            with open(mpath, "r") as f:
                s = f.read()
                m = LocalQueueMessage.from_json(s)
                if m.schema == END_OF_STREAM_SCHEMA:
                    return self._pull_eos(m, mpath)
                # make pending
                self._move_pending(m, mpath, int(time.time()) + self._lease)
                return m

    def _move_pending(self, m: LocalQueueMessage, mpath: str, timeout: int):
        fn = os.path.basename(mpath)
        pfn = f"{timeout}--{fn}"
        ppath = os.path.join(self._pending_path, pfn)
        shutil.move(mpath, ppath)
        m._pendingPath = ppath
        m._origPath = mpath
        m._queue = self
        self._log(fn, MsgState.Pending)
        # with open(self._log_file, "a") as f:
        #     f.write(f"{fn},{MsgState.Pending},{int(time.time())}")

    def _pull_eos(self, m: LocalQueueMessage, mpath: str) -> AcknowledgableQueueMessage:
        if self.has_pending_messages():
            self._move_pending(m, mpath, EOS_LABEL)
            return None
        else:
            return m

    def has_pending_messages(self) -> bool:
        for f in glob.glob(self._pending_glob):
            if os.path.isfile(f):
                return True
        return False

    def _get_msg_index(self, highest: bool) -> Union[int, None]:
        fl = sorted(filter(os.path.isfile, glob.glob(self._msg_glob)), reverse=highest)
        if len(fl) == 0:
            return None
        p = fl[0]
        s = Path(p).stem
        return int(s)

    def _calc_queue_timeout(self, max_timeout) -> float:
        p = re.compile("(\d+)--(\d+)")
        now = int(time.time())
        timeout = max_timeout
        found_eos = False
        for i, pp in enumerate(filter(os.path.isfile, glob.glob(self._pending_glob))):
            m = p.match(os.path.basename(pp))
            if not m:
                raise Exception(f"Unexpected pending message file name - '{pp}'")
            mtout = int(m[1])
            if found_eos and mtout == EOS_LABEL:
                # additional EOS - remove
                pathlib.Path(pp).unlink(missing_ok=True)
                continue
            rem = mtout - now
            found_eos = mtout == EOS_LABEL
            is_single_eos = i == 0 and found_eos
            if rem <= 0 or is_single_eos:
                # timed out - put back in service
                msg = f"{m[2]}.json"
                mp = os.path.join(self._path, msg)
                shutil.move(pp, mp)
                logger.debug(f"Queue#{self._name} restoring msg '{mp}'")
                self._get_queue().put(mp)
                timeout = 0
                self._log(msg, MsgState.Timedout)
                # with open(self._log_file, "a") as f:
                #     f.write(f"{msg},{MsgState.Timedout},{now}")
            elif rem < timeout:
                timeout = rem
        return timeout

    def _get_queue(self):
        while self._queue == None:
            with self._lock:
                # create message queue and pre-fill it
                queue = SimpleQueue()
                with FileLock(self._lock_file):
                    for fn in sorted(filter(os.path.isfile, glob.glob(self._msg_glob))):
                        logger.debug(f"Queue#{self._name} adding msg '{fn}'")
                        queue.put(fn)

                # track new incoming messages
                msg_glob = self._msg_glob
                qname = self._name

                class Handler(FileSystemEventHandler):
                    def on_closed(self, event):
                        mpath = event.src_path
                        if fnmatch.fnmatch(mpath, msg_glob):
                            logger.debug(f"Queue#{qname} adding msg '{mpath}'")
                            queue.put(mpath)

                self._queue = queue
                self._observer = Observer()
                self._observer.schedule(Handler(), self._path)
                self._observer.start()
        return self._queue

    def _log(self, path: str, state: MsgState):
        with open(self._log_file, "a") as f:
            f.write(f"{os.path.basename(path)},{state},{int(time.time())}\n")

    def __repr__(self):
        return f"<LocalQueue path={self._path}>"


class TestQueue(BaseQueue):
    def __init__(
        self,
        urn: str,
        adapter: LocalIOAdapter,
        lease: float = DEF_LEASE_TIME_SEC,
        timeout: float = DEF_MAX_WAIT_TIME_SEC,
    ) -> None:
        super().__init__(urn, adapter, lease, timeout)

        self._queue = []
        mpath = urn[len("urn:file://") :]
        if os.path.isdir(mpath):
            for f in glob.glob(os.path.join(mpath, "*.json")):
                self.__fill_q(f)
        else:
            self.__fill_q(mpath)

    def __fill_q(self, mpath):
        with open(mpath, "r") as f:
            s = f.read()
            self._queue.append(LocalQueueMessage.from_json(s))

    def push(self, m: QueueMessage) -> URN:
        raise Exception("TestQueue: 'push' not supported")

    def pull(self) -> AcknowledgableQueueMessage:
        if self._is_closed or len(self._queue) == 0:
            return LocalQueueMessage(schema=END_OF_STREAM_SCHEMA, content={})
        else:
            m = self._queue.pop(0)
            self._is_closed = len(self._queue) == 0
            return m

    def __repr__(self):
        return f"<TestQueue urn={self._urn}>"


class QueueIter:
    def __init__(self, queue: Queue) -> None:
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
    if u.scheme == "" or u.scheme == "file":
        path = u.path
    elif u.scheme == "urn":
        from ..ivcap import get_config  # break import loop

        if u.fragment != "":
            dname = u.fragment
        else:
            prefix = f"{get_config().SCHEMA_PREFIX}{resource.value}."
            plen = len(prefix)
            if len(urn) < plen:
                raise ValueError(
                    f"URN'{urn}'is not a valid one for resource '{resource.value}'"
                )
            dname = urn[plen:]
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


class LocalQueueService(QueueService):
    """
    Concrete implementation of QueueService for local queues.
    """

    def __init__(self):
        self.queues = {}

    def list(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict]:
        """
        List all queues.
        """
        # Implementing limit and offset for demonstration purposes
        # In a real scenario, these might not be directly applicable to local queues
        # and would need to be implemented differently
        #
        # The queues are returned as a list of dictionaries with the following keys
        # - name: the name of the queue
        # - description: the description of the queue
        # - policy: the policy of the queue

        return (
            [
                {"name": name, "description": None, "policy": None}
                for name in list(self.queues.keys())[offset:limit]
            ]
            if limit
            else [
                {"name": name, "description": None, "policy": None}
                for name in list(self.queues.keys())
            ]
        )

    def create(
        self, name: str, description: Optional[str] = None, policy: Optional[str] = Dict
    ) -> None:
        """
        Create a new queue with the given name.
        """
        for queue_name in self.queues:
            if queue_name == name:
                raise ValueError(f"Queue '{name}' already exists.")

        self.queues[name] = StdQueue()

        return {
            "id": f"urn:ivcap:queue:{name}",
            "name": name,
            "description": description,
            "created-at": "2024-04-18T23:04:17Z",
            "account": "urn:ivcap:account:a4c8f763-29e6-4d20-b739-9a8d5c2e14f2",
        }

    def delete(self, queue_id: str) -> None:
        """
        Delete the queue with the given name.
        """
        if queue_id not in self.queues:
            raise ValueError(f"Queue '{queue_id}' does not exist.")
        del self.queues[queue_id]

    def enqueue(self, queue_id: str, message: Dict) -> None:
        """
        Enqueue a message into the queue with the given name.
        """
        if queue_id not in self.queues:
            raise ValueError(f"Queue '{queue_id}' does not exist.")
        self.queues[queue_id].put(message)

    def dequeue(
        self, queue_id: str, limit: Optional[int] = 1
    ) -> List[Dict]:
        """
        Dequeue messages from the queue with the given name.
        """
        if queue_id not in self.queues:
            raise ValueError(f"Queue '{queue_id}' does not exist.")
        messages = []
        for _ in range(limit):
            try:
                message = self.queues[queue_id].get_nowait()
                messages.append(message)
            except Empty:
                # Queue is empty, exit the loop gracefully
                break
            except (ValueError, TypeError) as e:
                # Catch other relevant exceptions for the queue implementation
                logger.error(
                    f"Error while dequeuing message from queue '{queue_id}': {e}"
                )
                break
        return messages

    def read(self, queue_id: str) -> Dict:
        """
        Read the queue with the given name.
        """
        if queue_id not in self.queues:
            raise ValueError(f"Queue '{queue_id}' does not exist.")
        try:
            return self.queues[queue_id].queue[0]
        except IndexError:
            raise ValueError(f"Queue '{queue_id}' is empty.")
