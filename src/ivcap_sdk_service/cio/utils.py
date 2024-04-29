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
    cache_id = None
    content_type = None
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        content_type = r.headers.get('Content-Type')
        cache_id = r.headers.get('X-Cache-Id')
        logger.debug(f"cio#download: request {r} - {content_type} - {r.headers}")

        # if ct:
        #     cname = f"{cname}.{ct.replace('/', '.')}"
        # (fh, path) = self.cacheIO.get_fd(cname)
        # logger.info(f"Downloading {url} to cache {path}")

        for chunk in r.iter_content(chunk_size=chunk_size): # 8192): 
            #logger.info(f"chunk {chunk}")
            # If you have chunk encoded response uncomment if
            # and set chunk_size parameter to None.
            #if chunk: 
            fhdl.write(chunk)
    fhdl.flush()
    if close_fhdl:         
        fhdl.close()
    return (content_type, cache_id)

def get_cache_name(url: Url) -> str:
    name = re.search('.*/([^/]+)', url)[1]
    encoded_name = f"{sha256(url.encode('utf-8')).hexdigest()}-{name}"
    return encoded_name

def encode64(s: str) -> str:
    sb = s.encode('ascii')
    ba = base64.b64encode(sb)
    return ba.decode('ascii')
