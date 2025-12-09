#
# Copyright (c) 2025 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
import json
import os
import traceback
from typing import Callable, Optional, Union, BinaryIO, Any

from time import sleep
from urllib.parse import urlparse, urlunparse
import httpx
from pydantic import BaseModel, HttpUrl

from .events import EventReporter, BaseEvent
from .logger import getLogger
from .types import BinaryResult, ExecutionError, IvcapResult

logger = getLogger("ivcap")
event_logger = getLogger("app.event")

# Number of attempt to deliver job result before giving up
MAX_DELIVER_RESULT_ATTEMPTS = 4

OnResultF = Callable[[Union[IvcapResult, ExecutionError], str, Optional[str]], None]

result_callback: OnResultF = None

def set_result_callback(cbk: OnResultF):
    """
    Sets the result handler function to be used for processing job results.

    Args:
        handler: A callable that takes three arguments: the result, job_id,
        and the auth token of the incoming request.
    """
    global result_callback
    result_callback = cbk


def verify_result(result: Any, job_id: str, logger) -> Any:
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
    if result_callback is not None:
        # If a result handler is set, call it as well
        result_callback(result, job_id, authorization)

    ivcap_url = get_ivcap_url()
    if ivcap_url is None:
        # Make this library more useful outside the confines of IVCAP
        # if result_callback is None:
        #     logger.warning(f"{job_id}: no ivcap url found - cannot push result")
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


class SidecarReporter(EventReporter):
    def __init__(self, job_id: str, job_authorization: str):
        super().__init__(job_id, job_authorization)
        self._ivcap_url = get_ivcap_url()

    def _send(self, event: BaseEvent):
        event_logger.debug(f"{self.job_id}: {event.model_dump_json(exclude_none=True)}")
        if self._ivcap_url is None:
            return

        url = urlunparse(self._ivcap_url._replace(path=f"/events/{self.job_id}"))
        headers = {"Content-Type": "application/json"}
        if not (self.job_authorization == None or self.job_authorization == ""):
            headers["Authorization"] = self.job_authorization
        try:
            m = event.model_dump()
            data = json.dumps(m)
            response = httpx.post(
                url=url,
                headers=headers,
                data=data,
            )
            response.raise_for_status()
        except Exception as e:
            logger.warning(f"could not deliver event - {e}")

def get_ivcap_url() -> HttpUrl:
    """
    Returns the sidecar URL from the request headers.
    """
    base = os.getenv("IVCAP_BASE_URL")
    if base == "" or base is None:
        return None
    return urlparse(base)
