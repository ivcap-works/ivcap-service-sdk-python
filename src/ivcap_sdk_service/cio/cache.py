#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
from hashlib import sha256
import re
from pathlib import Path

from ..itypes import Url
from ..logger import sys_logger as logger

from .io_adapter import IOReadable


class Cache():
    """
    A storage adapter to fetch and cache remote artifacts 
    in a local directory.

    Attributes
    ----------
    cache_dir: str
        Path path to local cache directory, set via Config/API
    out_dir: str
        Path for output data, set via Config/API

    Methods
    -------
    get_and_cache_file(url: Url) -> IOReadable
        Return a readable for 'url'
    """
    def __init__(self, cache_dir: str) -> None:
        self.url2path = {}
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        from .local_io_adapter import LocalIOAdapter # avoid circular dependencies
        self.cacheIO = LocalIOAdapter(
            in_dir=cache_dir,
            out_dir=cache_dir
        )
        self._cache_dir = cache_dir

    def get_and_cache_file(self, url: Url) -> IOReadable:
        """Return a readable on a local file representing 'url'
        
        Before fetching the remote content, we check if a local
        copy has already been fetched previously. If yes, a IOReadable
        is returned on that local copy.
        
        If not, we first download the content into a local file in
        `_cache_dir` and then return a  IOReadable on that local
        file.
        
        Plese note, we currently do NOT check if the remote content
        has changed (no check on ETag)

        Args:
            url (Url): URL to content requested

        Returns:
            IOReadable: A readable on the content referenced by `url`
        """
        cname = get_cache_name(url)
        if self.cacheIO.readable_local(cname):
            logger.debug("Cache#get_and_cache_file: Hit! '%s' already cached as '%s'", url, cname)
            return self.cacheIO.read_local(cname)
        else:
            logger.debug("Cache#get_and_cache_file: Cache '%s' locally as '%s'", url, cname)
            return self.cacheIO.read_external(url, local_file_name=cname)

    def __repr__(self):
        return f"<Cache cache_dir={self._cache_dir}>"

def get_cache_name(url: Url) -> str:
    name = re.search('.*/([^/]+)', url)[1]
    encoded_name = f"{sha256(url.encode('utf-8')).hexdigest()}-{name}"
    return encoded_name
