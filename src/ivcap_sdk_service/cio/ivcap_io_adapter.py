#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
"""
Implementation of the IOAdapter class for use inside the IVCAP platform
"""
import os
from pathlib import Path
import sys
from typing import Callable, Dict, List, Optional, Sequence, Type, Union
from os import access, R_OK
from os.path import isfile
from urllib.parse import urlparse
import base64
import json
import requests

from ivcap_sdk_service.aspect import Aspect

from .readable_file import ReadableFile
from .readable_proxy import ReadableProxy
from ..itypes import URN, MetaDict, Url, SCHEMA_KEY
from ..logger import sys_logger as logger

from .io_adapter import Collection, IOAdapter, IOReadable, IOWritable, OnCloseF, Queue, QueueMessage, QueueService
from .writable_proxy import WritableProxy, upload_metadata

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
        queue_url: str = "http://queue.local",
    ) -> None:
        super().__init__()
        self.in_dir = os.path.abspath(in_dir)
        self.out_dir = os.path.abspath(out_dir)
        self.storage_url = storage_url
        self.cachable_url = cachable_url
        self.queue_url = queue_url

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

        if artifact_id.startswith("file://"):
            # Already locally available
            u = urlparse(artifact_id)
            return self.read_local(u.path, binary_content=binary_content)

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
        name = url
        if no_caching:
            curl = url
        else:
            if url.startswith(self.storage_url):
                curl = url
            else:
                curl = self.cachable_url(url)
        r = requests.head(curl)
        if r.status_code >= 400:
            raise Exception(f"cannot get HEAD of {curl}")
        n = r.headers.get('X-Artifact-Id')
        if n:
            name = n
        ior = ReadableProxy(curl, name=name, is_binary=binary_content)
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
        metadata: Optional[Union[MetaDict, Sequence[MetaDict]]] = None,
        seekable=False,
        is_binary: Optional[bool]=None,
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

        return WritableProxy(self.storage_url, mime_type, metadata, name, on_close=_on_close, is_binary=is_binary)

    def write_metadata(
        self,
        entity_id: str, # URN
        schema: str, # URN
        metadata: MetaDict,
        name: Optional[str] = None,
    ) -> str:
        if schema:
            metadata[SCHEMA_KEY] = schema
        return upload_metadata(self.storage_url, entity_id, metadata, name=name)

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
        return ReadableFile(name, path, None, is_binary=binary_content)

    def read_aspect(self, aspect_urn: URN, no_caching=False) -> dict:
        """Return an aspect as a dict

        Args:
            aspect_urn (URN): URN of aspect to read
            no_caching (bool, optional): If true, content is not cached nor read from cache. Defaults to False.

        Returns:
            dict: The content of the aspect as a dict
        """
        raise Exception("read_aspect: not implemented, yet")

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
        return IvcapCollection(collection_urn, self)

    def get_queue_service(self, **kwargs) -> QueueService:
        return IvcapQueueService(self.queue_url, **kwargs)

    def find_aspect(self,
                    schema: URN = None,
                    entity: URN = None,
                    json_path: str = None,
                    schema2type: Dict[str, Type[Aspect]] = None
    ) -> List[Aspect]:
        raise Exception("find_aspect: not implemented, yet")

    def get_queue(self, queue_urn: str) -> Queue:
        raise Exception("get_queue: not implemented, yet")

    def __repr__(self):
        return f"<IvcapIOAdapter in_dir={self.in_dir} out_dir={self.out_dir}>"

class IvcapCollection(Collection):
    def __init__(self, collection_urn: str, adapter: IvcapIOAdapter) -> None:
        super().__init__()
        self._collection_urn = collection_urn
        self._adapter = adapter

    @property
    def name(self) -> str:
        return self._collection_urn

    @property
    def urn(self) -> str:
        return self._collection_urn

    def __iter__(self):
        from ..ivcap import get_config # avoiding circular imports
        if self._collection_urn.startswith(get_config().QUEUE_PREFIX):
            return IvcapCollectionIter(self._collection_urn, self._adapter)
        else:
            return IvcapSingleIter(self._collection_urn, self._adapter)

    def __repr__(self):
        return f"<IvcapCollection urn={self._collection_urn}>"

class IvcapSingleIter:
    def __init__(self, artifact_urn: str, adapter: IvcapIOAdapter) -> None:
        self._artifact_urn = artifact_urn
        self._already_served = False
        self._adapter = adapter

    def __next__(self):
        if (self._already_served):
            raise StopIteration()

        self._already_served = True
        return self._adapter.read_artifact(self._artifact_urn)

class IvcapCollectionIter:
    def __init__(self, collection_urn: str, adapter: IvcapIOAdapter) -> None:
        self._urn = collection_urn
        self._url = adapter.cachable_url(collection_urn)
        self._adapter = adapter
        self._ack_token = None

    def __next__(self):
        self._send_ack() # for potentially previous artifact
        r = self._get_queue()
        if r.status_code == 204:
            # queue is empty
            raise StopIteration()
        if r.status_code == 307: # redirected to actual artifact
            h = r.headers
            art_urn = h["Location"]
            self._ack_token = h["X-Ack-Token"]
            a = self._adapter.read_external(art_urn)
            #a.as_local_file()
            return a
        logger.fatal(f"error response {r.status_code} while checking queue {self._urn}")
        sys.exit(-1)

    def _get_queue(self):
        try:
            logger.debug(f"Check queue '{self._urn}' if there is more")
            r = requests.get(self._url, allow_redirects=False)
            return r
        except:
            logger.fatal(f"while checking queue '{self._urn}' - {self._url} - {sys.exc_info()}")
            sys.exit(-1)

    def _send_ack(self):
        if not self._ack_token:
            return
        try:
            logger.debug(f"Ack artifact from queue '{self._urn}'")
            r = requests.delete(self._url, data=self._ack_token)
            self._ack_token = None
            return r
        except:
            logger.fatal(f"while ack previous artifact '{self._urn}' - {self._url} - {sys.exc_info()}")
            sys.exit(-1)

class IvcapQueue(Queue):
    """A queue of messages
    """
    @property
    def name(self) -> str:
        pass

    @property
    def urn(self) -> str:
        pass

    def push(self, m: QueueMessage) -> URN:
        pass

    def pull(self) -> QueueMessage:
        pass

class IvcapQueueService(QueueService):
    """
    An service for operating with IVCAP queues.
    """

    def __init__(self, base_url, timeout=10):
        """
        Initialises the service with the base URL and a requests timeout.
        """
        self.base_url = base_url
        self.timeout = timeout

    def _construct_url(self, endpoint):
        """
        Constructs the full URL for the given endpoint.
        """
        return f"{self.base_url}/1/queues/{endpoint}"

    def list(
        self,
        limit: int = 10,
        offset: int = 0,
        page: Optional[str] = None,
        filter: Optional[str] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False,
        at_time: Optional[str] = None,
    ) -> List[Dict]:
        """
        List queues with optional query parameters.

        This method retrieves a list of queues from the IVCAP service,
        with support for pagination, filtering, and sorting.

        Parameters
        ----------
        limit : int, optional
            The maximum number of items to return. Default is 10.
        offset : int, optional
            The number of items to skip before starting to return items. Default is 0.
        page : str, optional
            The page number for pagination.
        filter : str, optional
            A filter expression to apply to the results.
        order_by : str, optional
            The field to order the results by.
        order_desc : bool, optional
            Whether to order the results in descending order. Default is False.
        at_time : str, optional
            The time for historical data.

        Returns
        -------
        List[Dict]
            A list of queues, each represented as a dictionary.

        Raises
        ------
        requests.exceptions.RequestException
            If the request fails for any reason.

        Example
        -------
        >>> service = IvcapQueueService(base_url="http://queue.local")
        >>> queues = service.list(limit=5, order_by="name", order_desc=True)
        >>> print(queues)
        [{'id': '1', 'name': 'Queue1'}, {'id': '2', 'name': 'Queue2'}, ...]
        """
        # Construct the query parameters
        params = {
            "limit": limit,
            "offset": offset,
            "page": page,
            "filter": filter,
            "order-by": order_by,
            "order-desc": order_desc,
            "at-time": at_time,
        }

        # Remove None values from the query parameters
        params = {k: v for k, v in params.items() if v is not None}

        # Send the request
        try:
            logger.debug(f"List queues with params: {params}")
            url = self._construct_url("")
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to list queues: {e}")
            return []

    def create(self, name: str, description: str = None, policy: str = None) -> Dict:
        """
        Create a new queue with the given name and optional description and policy.

        This method creates a new queue in the IVCAP service with the given
        name and optional description and policy.

        Parameters
        ----------
        name : str
            The name of the queue to create.
        description : str, optional
            The description of the queue. Default is None.
        policy : str, optional
            The policy of the queue. Default is None.

        Returns
        -------
        Dict
            A dictionary representing the created queue.

        Raises
        ------
        ValueError
            If the 'name' parameter is not provided.
        requests.exceptions.RequestException
            If the request fails for any reason.

        Example
        -------
        >>> service = IvcapQueueService(base_url="http://queue.local")
        >>> queue = service.create(name="Queue1", description="My first queue")
        >>> print(queue)
        {'id': '1', 'name': 'Queue1', 'description': 'My first queue', ...}
        """
        if not name:
            raise ValueError("The 'name' parameter is required")

        # Construct the request data
        data = {
            "name": name,
            "description": description,
            "policy": policy,
        }

        # Remove None values from the request data
        data = {k: v for k, v in data.items() if v is not None}

        # Send the request
        try:
            logger.debug(f"Create queue with data: {data}")
            url = self._construct_url("")
            response = requests.post(url, json=data, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create queue: {e}")
            return {}

    def delete(self, queue_id: str) -> None:
        """
        Delete the queue with the given ID.

        This method deletes the queue with the given ID from the IVCAP service.

        Parameters
        ----------
        queue_id : str
            The ID of the queue to delete.

        Raises
        ------
        ValueError
            If the 'queue_id' parameter is not provided.
        requests.exceptions.RequestException
            If the request fails for any reason.

        Example
        -------
        >>> service = IvcapQueueService(base_url="http://queue.local")
        >>> service.delete(queue_id="1")
        """
        if not queue_id:
            raise ValueError("The 'queue_id' parameter is required")

        # Send the request
        try:
            logger.debug(f"Delete queue with ID: {queue_id}")
            url = self._construct_url(queue_id)
            response = requests.delete(url, timeout=self.timeout)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to delete queue: {e}")

    def read(self, queue_id: str) -> Dict:
        """
        Read the queue with the given ID.

        This method reads the queue with the given ID from the IVCAP service.

        Parameters
        ----------
        queue_id : str
            The ID of the queue to read.

        Returns
        -------
        Dict
            A dictionary representing the read queue.

        Raises
        ------
        ValueError
            If the 'queue_id' parameter is not provided.
        requests.exceptions.RequestException
            If the request fails for any reason.

        Example
        -------
        >>> service = IvcapQueueService(base_url="http://queue.local")
        >>> queue = service.read(queue_id="1")
        >>> print(queue)
        {'id': '1', 'name': 'Queue1', 'description': 'My first queue', ...}
        """
        if not queue_id:
            raise ValueError("The 'queue_id' parameter is required")

        # Send the request
        try:
            logger.debug(f"Read queue with ID: {queue_id}")
            url = self._construct_url(queue_id)
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to read queue: {e}")
            return {}

    def enqueue(self, queue_id: str, message: Dict) -> Dict:
        """
        Enqueue the given message into the queue with the given ID.

        This method enqueues the given message into the queue with the given ID
        in the IVCAP service.

        Parameters
        ----------
        queue_id : str
            The ID of the queue to enqueue the message into.
        message : Dict
            The message to enqueue into the queue.

        Returns
        -------
        Dict
            A dictionary representing the enqueued message.

        Raises
        ------
        ValueError
            If the 'queue_id' parameter is not provided.
        requests.exceptions.RequestException
            If the request fails for any reason.

        Example
        -------
        >>> service = IvcapQueueService(base_url="http://queue.local")
        >>> message = {"content": "Hello, world!"}
        >>> message = service.enqueue(queue_id="1", message=message)
        >>> print(message)
        {'id': '1', 'content': 'Hello, world!', 'content-type': 'application/json', ...}
        """
        if not queue_id:
            raise ValueError("The 'queue_id' parameter is required")

        # Send the request
        try:
            url = self._construct_url(f"{queue_id}/messages")

            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }

            params = {
                "schema": "urn:ivcap:schema:queue:message.1",
            }

            json_data = json.dumps(message)

            response = requests.post(
                url,
                params=params,
                headers=headers,
                json=json_data,
                timeout=self.timeout,
            )
            response.raise_for_status()

            if not response.content:
                logger.error("Failed to enqueue message: empty response received.")
                return {}

            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to enqueue message: {e}")
            return {}

    def dequeue(
        self, queue_id: str, limit: Optional[int] = 1
    ) -> List[Dict]:
        """
        Dequeue messages from the queue with the given ID.

        This method dequeues messages from the queue with the given ID in the

        Parameters
        ----------
        queue_id : str
            The ID of the queue to dequeue messages from.
        limit : int, optional
            The number of messages to fetch from the queue. Default is 1.

        Returns
        -------
        List[Dict]
            A list of dictionaries representing the dequeued messages.

        Raises
        ------
        ValueError
            If the 'queue_id' parameter is not provided.
        requests.exceptions.RequestException
            If the request fails for any reason.

        Example
        -------
        >>> service = IvcapQueueService(base_url="http://queue.local")
        >>> messages = service.dequeue(queue_id="1", limit=3)
        >>> print(messages)
        [{'id': '1', 'content': 'Hello, world!', 'content-type': 'application/json', ...}, ...]
        """
        if not queue_id:
            raise ValueError("The 'queue_id' parameter is required")

        # Construct the query parameters
        params = {"messageFetchCount": f"{limit}"}

        # Send the request
        try:
            logger.debug(f"Dequeue messages from queue with ID: {queue_id}")
            url = self._construct_url(f"{queue_id}/messages")
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            if not response.content:
                logger.error("Failed to enqueue message: empty response received.")
                return []

            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to dequeue messages: {e}")
            return []
