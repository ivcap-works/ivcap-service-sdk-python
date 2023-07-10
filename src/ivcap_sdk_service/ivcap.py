#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
from __future__ import annotations
#
# Helper funtions to interface with CSE services
#
from argparse import ArgumentParser
from typing import Callable, Dict, Any, Optional, Sequence, Union, cast
from urllib.parse import urlparse

#from .utils import json_dump

from .cio.io_adapter import IOAdapter, IOReadable, IOWritable, OnCloseF

from .logger import sys_logger as logger
from .config import Config, Resource
from .itypes import MetaDict, SupportedMimeTypes, Url, MissingParameterValue, UnsupportedMimeType

SCHEMA_KEY = '$schema'

DELIVERED = []
_CONFIG: Config = None # only use internally and only after calling init()

SaverF = Callable[[
    str, # name
    Any, # data
    IOAdapter, # io_adapater
    Optional[str], # collection_name
    Optional[MetaDict], # metadata = {}
    bool, # seekable = False
    Optional[OnCloseF] # on_close
], None]

_CLASS2MIME_TYPE = {
    # "<class 'xarray.core.dataset.Dataset'>": NETCDF_MT,
    # "<class 'xarray.core.dataarray.DataArray'>": NETCDF_MT,
}

_MIME_TYPE2SAVER: Dict[str, SaverF] = {
    # NETCDF_MT: xa_dataset_saver,
}

def deliver_data(
    name: str, 
    data_or_lambda: Union[Any, Callable[[IOWritable], None]],
    mime_type: Union[str, SupportedMimeTypes], 
    collection_name: Optional[str] = None,
    metadata: Optional[Union[MetaDict, Sequence[MetaDict]]] = None, 
    seekable=False,
    on_close: Optional[OnCloseF] = None
):
    """Deliver a result of this service

    Args:
        name (str): A user friendly name
        data_or_lambda (Union[Any, Callable[[IOWritable], None]]): The data to deliver. Either directly or a callback 
             providing a file-like handle to provide the data then.
        mime_type (Union[str, SupportedMimeTypes]): The mime type of the data. Anything not starting with 'text' is assumed to be a binary content
        collection_name (Optional[str], optional): Optional collection name. Defaults to None.
        metadata (Optional[Union[MetaDict, Sequence[MetaDict]]], optional): Key/value pairs (or list of k/v pairs) to add as metadata. Defaults to None.
        seekable (bool, optional): If true, writable should be seekable (needed for NetCDF). Defaults to False.
        on_close (Optional[Callable[[Url]]], optional): Called with assigned artifact ID. Defaults to None.

    Raises:
        NotImplementedError: Raised when no saver function is defined for 'type'

    Returns:
        None
    """

    global DELIVERED

    def _on_close(url):
        mt = mime_type.value if isinstance(mime_type, SupportedMimeTypes) else mime_type
        m = dict(name=name, url=url, mime_type=mt, meta=metadata)
        DELIVERED.append(m)
        notify(m, _CONFIG.SCHEMA_PREFIX + 'deliver')
        if on_close:
            on_close(url)

    if callable(data_or_lambda):
        l = cast(Callable[[IOWritable], None],  data_or_lambda)
        if not mime_type:
            raise MissingParameterValue('mime_type')
        fhdl: IOWritable = get_config().IO_ADAPTER.write_artifact(mime_type, name, collection_name, metadata, seekable, _on_close)
        l(fhdl)
        fhdl.close()
    else: 
        data = data_or_lambda
        if not mime_type:
            cls = str(type(data))
            mime_type = _CLASS2MIME_TYPE.get(cls)
            if not mime_type:
                raise NotImplementedError(f"Cannot resolve mime-type for '{cls}'")

        sf = _MIME_TYPE2SAVER.get(mime_type)
        if sf:
            sf(name, data, get_config().IO_ADAPTER, 
            collection_name=collection_name, metadata=metadata, seekable=seekable, on_close=_on_close)
        else:
            raise UnsupportedMimeType(mime_type)

def register_saver(mime_type: str, obj_type: Any, saverF: SaverF):
    """Register a 'saver' function used in 'deliver' for a specific data type.

    Args:
        mime_type (str): Mime type to use for that data type
        obj_type (Any): The class this saver is for
        saverF (SaverF): Function to deliver an instance of `obj_type`
    """
    _CLASS2MIME_TYPE[str(obj_type)] = mime_type
    _MIME_TYPE2SAVER[mime_type] = saverF

def create_metadata(schema: str, mdict:Optional[MetaDict] = {}, **args) -> Dict:
    """Return a dict which has a 'proper' schema declaration added.

    Args:
        schema (str): Schema URN

    Returns:
        Dict: A copy of 'args' plus a 'SCHEMA_KEY' entry
    """
    d = dict(mdict, **args)
    d['$schema'] = schema
    return d

def fetch_data(url: Url, binary_content=True, no_caching=False, seekable=False) -> IOReadable:
    """Return an 'IOReadable' on the content referenced by 'url'.
    
    This simply calls 'cio.IOAdapter.read_artifact' through the 
    configured 'IOAdapter'.

    Args:
        url (Url): Url to content
        binary_content (bool, optional): Indicates if content is binary [True].
        no_caching (bool, optional): Indicates if content should NOT be cached [False].
        seekable (bool, optional): Indicates if Readable should be seekable [False].

    Returns:
        IOReadable: A readable on the referenced content
    """
    return get_config().IO_ADAPTER.read_artifact(url, binary_content, no_caching, seekable)

def get_order_id():
    """Returns the ID of the currently processed order"""
    return get_config().ORDER_ID


def get_node_id():
    """Returns the ID of this computational entity"""
    return get_config().NODE_ID

class ExitException(Exception):
    def __init__(self, msg):
        self.msg = msg
            

def notify(msg, schema=None):
    """Publish 'msg' to indicate progress."""
    from .utils import json_dump
    p = False # _get_kafka_producer()
    if p:
        h = [
            ('Content-Type', b'application/json'),
            ('CAYP-Order-ID', get_order_id().encode("UTF-8")),
            ('CAYP-Node-ID', get_node_id().encode("UTF-8"))
        ]
        if schema:
            h.append(('Content-Schema', schema.encode('utf-8')))

        js = json_dump(msg)
        # this is a bit of a hack, but ...
        if (js.startswith('{')):
            extra = {'@order_id': get_order_id(), '@node_id': get_node_id()}
            if schema:
                extra['@schema'] = schema
            jx = json_dump(extra)
            js = f"{js[0]}{jx[1:-1]},{js[1:]}"
    else:
        logger.debug(f"Notify {json_dump(msg)}")

def get_config() -> Config:
    return _CONFIG


#### Initialize

def init(argv:Dict[str, str] = None, modify_ap: Callable[[ArgumentParser], ArgumentParser] = None):
    global _CONFIG
    _CONFIG = Config(argv, modify_ap)

    from .savers import register_savers # avoid circular dependencies
    register_savers()
