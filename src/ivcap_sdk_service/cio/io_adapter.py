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
        """
        Returns the I/O mode of the adapter.

        :return: A string representing the I/O mode of the adapter.
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Returns the name of the IO adapter.

        :return: A string representing the name of the IO adapter.
        """

    @abstractmethod
    def close(self) -> None:
        """
        Closes the IO adapter and releases any system resources associated with it.
        """

    @property
    @abstractmethod
    def closed(self) -> bool:
        """
        Returns a boolean indicating whether the IO adapter is closed or not.
        """

    @abstractmethod
    def readable(self) -> bool:
        """
        Returns True if the IO object is readable, False otherwise.
        """

    @abstractmethod
    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        """
        Change the stream position to the given byte offset.

        :param offset: The byte offset to seek to.
        :param whence: Optional. The reference point used to determine the new position. Defaults to io.SEEK_SET.
        :return: The new absolute position.
        """

    @abstractmethod
    def seekable(self) -> bool:
        """
        Return True if the stream supports random access (i.e., if it has a seek method).
        """

    @abstractmethod
    def tell(self) -> int:
        """
        Returns the current position of the file pointer in the stream.

        :return: The current position of the file pointer.
        :rtype: int
        """

    @abstractmethod
    def writable(self) -> bool:
        """
        Returns True if the IO object is open for writing, False otherwise.
        """


class IOReadable(_IOBase):
    """
    Abstract base class for readable IO adapters.

    Subclasses must implement the `urn`, `read`, `readline`, `readlines`, and `as_local_file` methods.
    """

    @property
    @abstractmethod
    def urn(self) -> str:
        """
        Returns the Uniform Resource Name (URN) for the input/output adapter.

        :return: A string representing the URN for the adapter.
        """

    @property
    @abstractmethod
    def mime_type(self) -> str:
        """
        Returns the MIME type of the data being read or written by the adapter.

        :return: A string representing the MIME type of the data.
        """

    @abstractmethod
    def read(self, n: int = -1) -> AnyStr:
        """
        Read up to n bytes from the input stream.

        Args:
            n (int): The maximum number of bytes to read. If not specified, or negative, read until EOF.

        Returns:
            AnyStr: The data read from the input stream, as bytes or a string depending on the input mode.
        """

    @abstractmethod
    def readline(self, limit: int = -1) -> AnyStr:
        """
        Read and return one line from the input stream.

        If limit is specified, at most limit bytes will be read.

        :param limit: (optional) Maximum number of bytes to read.
        :type limit: int
        :return: The next line from the input stream.
        :rtype: bytes or str
        """

    @abstractmethod
    def readlines(self, hint: int = -1) -> List[AnyStr]:
        """
        Read and return a list of lines from the stream.

        Args:
            hint (int): Optional. The number of bytes to read. Defaults to -1, which means to read until EOF.

        Returns:
            List[AnyStr]: A list of lines read from the stream.
        """

    @property
    @abstractmethod
    def as_local_file(self) -> str:
        """
        Returns the path to a local file that can be used to access the data represented by this IOAdapter.
        """


class IOWritable(_IOBase):
    """
    A base class for writable IO objects.

    Subclasses must implement the abstract methods `write`, `writelines`, `truncate`, and `flush`.
    Additionally, subclasses must implement the `urn` property, which should return a string representing
    the unique resource identifier for the IO object.
    """

    @property
    @abstractmethod
    def urn(self) -> str:
        """
        Returns the Uniform Resource Name (URN) for the IO adapter.

        :return: A string representing the URN for the IO adapter.
        """

    @abstractmethod
    def write(self, bytes_obj: AnyStr) -> int:
        """
        Writes the given string to the output stream.

        Args:
            bytes_obj (AnyStr): The string to write to the output stream.

        Returns:
            int: The number of characters written to the output stream.
        """

    @abstractmethod
    def writelines(self, lines: List[AnyStr]) -> None:
        """
        Write a list of lines to the output stream.

        Args:
            lines (List[AnyStr]): A list of lines to write to the output stream.

        Returns:
            None
        """

    @abstractmethod
    def truncate(self, size: int = None) -> int:
        """
        Truncates the file to the specified size (in bytes).

        Args:
            size (int, optional): The size (in bytes) to truncate the file to. If not specified, the file will be truncated to 0 bytes.

        Returns:
            int: The new size of the file (in bytes) after truncation.
        """

    @abstractmethod
    def flush(self) -> None:
        """
        Flushes the write buffer of the IO adapter.
        """


class IO_ReadWritable(IOReadable, IOWritable):
    """
    A class that represents an object that can be both read from and written to.

    This class inherits from the IOReadable and IOWritable classes, which provide the read and write functionality, respectively.
    """


class Collection(ABC):
    """A collection of artifacts

    Args:
        ABC (_type_): _description_
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Returns the name of the IO adapter.
        """


OnCloseF = Callable[[Url], None]


class IOAdapter(ABC):
    """
    Abstract base class for input/output (IO) adapters that provide a uniform interface for reading and writing artifacts
    and metadata. Subclasses of this class must implement the abstract methods defined here.
    """

    @abstractmethod
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

    @abstractmethod
    def artifact_readable(self, artifact_id: str) -> bool:
        """Return true if artifact exists and is readable

        Args:
            artifact_id (str): ID of artifact

        Returns:
            bool: True if artifact can be read
        """

    @abstractmethod
    def write_artifact(
        self,
        mime_type: str,
        name: Optional[str] = None,
        collection_name: Optional[str] = None,
        metadata: Optional[Union[MetaDict, Sequence[MetaDict]]] = None,
        seekable=False,
        on_close: Optional[OnCloseF] = None,
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

    @abstractmethod
    def write_metadata(
        self,
        entity_id: str,  # URN
        schema: str,  # URN
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

    @abstractmethod
    def get_collection(self, collection_urn: str) -> Collection:
        """Return a collection representing a set of artifacts

        Args:
            collection_urn (URN): Collection identifies

        Returns:
            Collection: An instance of a collection object appropriate for
            the current context
        """
