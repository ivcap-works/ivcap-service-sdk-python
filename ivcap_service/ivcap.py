#
# Copyright (c) 2025 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
import json
import os
import traceback
from typing import Optional, Union, BinaryIO

from time import sleep
from urllib.parse import urlparse, urlunparse
import httpx
from pydantic import BaseModel, HttpUrl

from .logger import getLogger
from .types import BinaryResult, ExecutionError, IvcapResult

logger = getLogger("ivcap")

# Number of attempt to deliver job result before giving up
MAX_DELIVER_RESULT_ATTEMPTS = 4


def verify_result(result: any, job_id: str, logger) -> any:
    if isinstance(result, ExecutionError):
        return result
    if isinstance(result, BaseModel):
        try:
            return IvcapResult(
                content=result.model_dump_json(by_alias=True),
                content_type="application/json",
                raw=result,
            )
        except Exception as ex:
            msg = f"{job_id}: cannot json serialise pydantic isntance - {str(ex)}"
            logger.warning(msg)
            return ExecutionError(
                error=msg,
                type=type(ex).__name__,
                traceback=traceback.format_exc()
            )
    if isinstance(result, BinaryResult):
        return IvcapResult(content=result.content, content_type=result.content_type)
    if isinstance(result, str):
        return IvcapResult(content=result, content_type="text/plain", raw=result)
    if isinstance(result, bytes):
        # If it's a byte array, return it as is
        return IvcapResult(
            content=result,
            content_type="application/octet-stream",
            raw=result,
        )
    if isinstance(result, BinaryIO):
        # If it's a file handler, return it as is
        return IvcapResult(
            content=result,
            content_type="application/octet-stream",
            raw=result
        )
    # normal model which should be serialisable
    try:
        result = IvcapResult(
            content=json.dumps(result),
            content_type="application/json"
        )
    except Exception as ex:
        msg = f"{job_id}: cannot json serialise result - {str(ex)}"
        logger.warning(msg)
        result = ExecutionError(
            error=msg,
            type=type(ex).__name__,
        )

def push_result(result: Union[IvcapResult, ExecutionError], job_id: str, authorization: Optional[str]=None):
    """Actively push result to sidecar, fail quietly."""
    ivcap_url = get_ivcap_url()
    if ivcap_url is None:
        logger.warning(f"{job_id}: no ivcap url found - cannot push result")
        return
    url = urlunparse(ivcap_url._replace(path=f"/results/{job_id}"))

    content_type="text/plain"
    content="SOMETHING WENT WRONG _ PLEASE REPORT THIS ERROR"
    is_error = False
    if not (isinstance(result, ExecutionError) or isinstance(result, IvcapResult)):
        msg = f"{job_id}: expected 'IvcapResult' or 'ExecutionError' but got {type(result)}"
        logger.warning(msg)
        result = ExecutionError(
            error=msg,
            type='InternalError',
        )

    if isinstance(result, IvcapResult):
        content = result.content
        content_type = result.content_type
    else:
        is_error = True
        if not isinstance(result, ExecutionError):
            # this should never happen
            logger.error(f"{job_id}: expected 'ExecutionError' but got {type(result)}")
            result = ExecutionError(
                error="please report unexpected internal error - expected 'ExecutionError' but got {type(result)}",
                type="internal_error",
            )
        content = result.model_dump_json(by_alias=True)
        content_type = "application/json"


    wait_time = 1
    attempt = 0
    headers = {
        "Content-Type": content_type,
        "Is-Error": str(is_error),
    }
    if not (authorization == None or authorization == ""):
        headers["Authorization"] = authorization

    while attempt < MAX_DELIVER_RESULT_ATTEMPTS:
        try:
            response = httpx.post(
                url=url,
                headers=headers,
                data=content,
            )
            response.raise_for_status()
            return
        except Exception as e:
            attempt += 1
            logger.info(f"{job_id}: attempt #{attempt} failed to push result - will try again in {wait_time} sec - {type(e)}: {e}")
            sleep(wait_time)
            wait_time *= 2

    logger.warning(f"{job_id}: giving up pushing result after {attempt} attempts")


def get_ivcap_url() -> HttpUrl:
    """
    Returns the sidecar URL from the request headers.
    """
    base = os.getenv("IVCAP_BASE_URL")
    if base == "" or base is None:
        return None
    return urlparse(base)
