#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
import base64
from hashlib import sha256
import re
from typing import BinaryIO
import requests

from ..logger import sys_logger as logger
from ..itypes import Url


def download(url: Url, fhdl: BinaryIO, chunk_size=None, close_fhdl=True) -> (str, str):
    """
    Downloads the content from the given URL and writes it to the given file handle.

    Args:
        url (Url): The URL to download the content from.
        fhdl (BinaryIO): The file handle to write the downloaded content to.
        chunk_size (int, optional): The size of the chunks to download the content in. Defaults to None.
        close_fhdl (bool, optional): Whether to close the file handle after writing the content. Defaults to True.

    Returns:
        Tuple[str, str]: A tuple containing the content type of the downloaded content and the cache ID of the response.
    """
    cache_id = None
    content_type = None
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        content_type = r.headers.get("Content-Type")
        cache_id = r.headers.get("X-Cache-Id")
        logger.debug(f"cio#download: request {r} - {content_type} - {r.headers}")

        for chunk in r.iter_content(chunk_size=chunk_size):
            fhdl.write(chunk)
    fhdl.flush()
    if close_fhdl:
        fhdl.close()
    return (content_type, cache_id)


def get_cache_name(url: str) -> str:
    """
    Returns a unique cache name for the given URL.

    Args:
        url (str): The URL to generate a cache name for.

    Returns:
        str: A unique cache name for the given URL.
    """
    name = re.search(".*/([^/]+)", url)[1]
    encoded_name = f"{sha256(url.encode('utf-8')).hexdigest()}-{name}"
    return encoded_name


def encode64(s: str) -> str:
    """
    Encodes a string to base64.

    Args:
        s (str): The string to be encoded.

    Returns:
        str: The base64-encoded string.
    """
    sb = s.encode("ascii")
    ba = base64.b64encode(sb)
    return ba.decode("ascii")
