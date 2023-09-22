#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
from abc import ABC, abstractmethod
from typing import AnyStr, List, Callable, Optional, Sequence, Union
import io

from ..itypes import MetaDict, Url

class _IOBase(ABC):
    @property
    @abstractmethod
    def mode(self) -> str:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    @property
    @abstractmethod
    def closed(self) -> bool:
        pass

    @abstractmethod
    def readable(self) -> bool:
        pass

    @abstractmethod
    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        pass

    @abstractmethod
    def seekable(self) -> bool:
        pass

    @abstractmethod
    def tell(self) -> int:
        pass

    @abstractmethod
    def writable(self) -> bool:
        pass

    @abstractmethod
    def close(self) -> None:
        pass

class IOReadable(_IOBase):
    @property
    @abstractmethod
    def urn(self) -> str:
        pass
    
    @property
    @abstractmethod
    def mime_type(self) -> str:
        pass
    
    @abstractmethod
    def read(self, n: int = -1) -> AnyStr:
        pass

    @abstractmethod
    def readline(self, limit: int = -1) -> AnyStr:
        pass

    @abstractmethod
    def readlines(self, hint: int = -1) -> List[AnyStr]:
        pass

    @property
    @abstractmethod
    def as_local_file(self) -> str:
        pass

class IOWritable(_IOBase):
    @property
    @abstractmethod
    def urn(self) -> str:
        pass

    @abstractmethod
    def write(self, s: AnyStr) -> int:
        pass

    @abstractmethod
    def writelines(self, lines: List[AnyStr]) -> None:
        pass

    @abstractmethod
    def truncate(self, size: int = None) -> int:
        pass

    @abstractmethod
    def flush(self) -> None:
        pass


class IO_ReadWritable(IOReadable, IOWritable):
    pass

class Collection(ABC):
    """A collection of artifacts

    Args:
        ABC (_type_): _description_
    """
    @property
    @abstractmethod
    def name(self) -> str:
        pass

class Collection(ABC):
    """A collection of artifacts
    """
    @property
    @abstractmethod
    def name(self) -> str:
        pass

OnCloseF = Callable[[Url], None]

class IOAdapter(ABC):

    # @classmethod
    # def create_cache(cls, cache_dir: str, cache_proxy_url: str):
    #     return None

    @abstractmethod
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
        pass

    # @abstractmethod
    # def read_external(self, url: Url, binary_content=True, no_caching=False, seekable=False) -> IOReadable:
    #     """Return a readable file-like object providing the content of an external data item.

    #     Args:
    #         url (Url): URL of external object to read
    #         binary_content (bool, optional): If true content is expected to be of binary format otherwise text is expected. Defaults to True.
    #         no_caching (bool, optional): If set, content is not cached nor read from cache. Defaults to False.
    #         seekable (bool, optional): If true, returned readable should be seekable

    #     Returns:
    #         IOReadable: The content of the external data item as a file-like object
    #     """
    #     pass

    @abstractmethod
    def artifact_readable(self, artifact_id: str) -> bool:
        """Return true if artifact exists and is readable

        Args:
            artifact_id (str): ID of artifact

        Returns:
            bool: True if artifact can be read
        """
        pass

    @abstractmethod
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
            metadata (Optional[MetaDict | List[MetaDict]], optional): Key/value pairs (or list of key/value pairs) to add as metadata. Defaults to {}.
            seekable (bool, optional): If true, writable should be seekable (needed for NetCDF). Defaults to False.
            on_close (Optional[OnCloseF], optional): Called with assigned artifact ID. Defaults to None.

        Returns:
            IOWritable: A file-like object to write deliver artifact content - needs to be closed
        """
        pass
    
    @abstractmethod
    def write_artifact(
        self,
        mime_type: str, 
        *,
        name: Optional[str] = None,
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
            metadata (Optional[MetaDict | List[MetaDict]], optional): Key/value pairs (or list of key/value pairs) to add as metadata. Defaults to {}.
            seekable (bool, optional): If true, writable should be seekable (needed for NetCDF). Defaults to False.
            on_close (Optional[OnCloseF], optional): Called with assigned artifact ID. Defaults to None.

        Returns:
            IOWritable: A file-like object to write deliver artifact content - needs to be closed
        """
        pass
    
    @abstractmethod
    def write_metadata(
        self,
        entity_id: str, # URN
        schema: str, # URN
        metadata: MetaDict,
    ) -> str:
        """Add a 'metadata' aspect to 'entity_id' with 'schema'.

        Args:
            entity_id (URN): Entity URN the metadata should be attached to
            schema (URN): Schema used in 'metadata'
            metadata (MetaDict): Metadata (aspect) to be attached to 'entity_id'

        Returns:
            str: Metadata record URN
        """
        pass

    @abstractmethod
    def get_collection(self, collection_urn: str) -> Collection:
        """Return a collection representing a set of artifacts

        Args:
            collection_urn (URN): Collection identifies

        Returns:
            Collection: An instance of a collection object appropriate for
            the current context
        """
        pass
