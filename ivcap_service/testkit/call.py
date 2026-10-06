#
# Copyright (c) 2025 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
"""
Generic HTTP call worker function (used for the 'call' section of a
'test-batch' Request).
"""

from typing import Any

import httpx
from pydantic import BaseModel, Field, HttpUrl

from ivcap_service import JobContext


class CallTester(BaseModel):
    method: str = Field(
        ...,
        description="The HTTP method to use (GET, POST, PUT, DELETE, etc.).",
        pattern="^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)$",  # Only allow valid methods
    )
    url: HttpUrl = Field(..., description="The full URL of the API endpoint.")
    params: dict[str, Any] | None = Field(
        None,
        description="Optional dictionary of query parameters to be appended to the URL.",
    )
    data: dict[str, Any] | None = Field(
        None,
        description="Optional JSON payload to be sent in the request body (for POST/PUT).",
    )
    headers: dict[str, str] | None = Field(
        None, description="Optional dictionary of headers to include in the request."
    )
    timeout: int = Field(
        5,
        description="The timeout duration for the request in seconds.",
        ge=1,  # Minimum value of 1 second to prevent infinite waiting
    )


def make_request(req: CallTester, ctxt: JobContext) -> Any:
    """
    Makes a generic HTTP request.

    Note: unlike the other sub-tests, this one has no fixed result shape -
    the response body is whatever JSON the called endpoint happens to
    return (or an '{"error": ...}' dict on failure), so it can't be
    usefully modeled as a dedicated Pydantic result type.

    :param req: CallTester object containing request details.
    :return: JSON response or error message.
    """
    with ctxt.report.step(
        "make_call",
        f"Making HTTP call to {req.url}",
        url=req.url,
        method=req.method,
        params=req.params,
        data=req.data,
        headers=req.headers,
        timeout=req.timeout,
    ):
        try:
            url = str(req.url)
            response = httpx.request(
                method=req.method.upper(),
                url=url,
                params=req.params,
                json=req.data,
                headers=req.headers,
                timeout=req.timeout,
            )
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx, 5xx)
            return response.json()

        except httpx.HTTPError as e:
            return {"error": str(e)}
