#
# Copyright (c) 2025 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#

# Various "patches" to maiontain context between incoming requests
# and calls to external services within a "session"
#
from dataclasses import dataclass
import functools
from logging import Logger
from ivcap_service import getLogger
import os
from typing import Any, Callable, Literal, Optional
from httpx import URL as URLx
from urllib.parse import urlparse

import urllib

from .types import JobContext

ExecContextF = Callable[[], JobContext]

def otel_instrument(
    with_telemetry: Optional[Literal[True]],
    extension: Optional[Callable[[str], None]],
    logger: Logger,
):
    if with_telemetry == False:
        return
    endpoint = os.environ.get('OTEL_EXPORTER_OTLP_ENDPOINT')
    if endpoint == None:
        if with_telemetry == True:
            logger.warning("requested --with-telemetry but exporter is not defined")
        return

    if os.environ.get("PYTHONPATH") == None:
            os.environ["PYTHONPATH"] = ""
    import opentelemetry.instrumentation.auto_instrumentation.sitecustomize # force internal settings
    logger.info(f"instrumenting for endpoint {endpoint}")
    if extension != None:
        extension(endpoint)
    # Also instrumemt
    try:
        from opentelemetry.instrumentation.requests import RequestsInstrumentor
        RequestsInstrumentor().instrument()
    except ImportError:
        pass
    try:
        import httpx # checks if httpx library is even used by this tool
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        HTTPXClientInstrumentor().instrument()
    except ImportError:
        pass

def extend_requests(context_f: ExecContextF):
    from requests import Session, PreparedRequest

    logger = getLogger("app.request")

    # Save original function
    wrapped_send = Session.send

    @functools.wraps(wrapped_send)
    def _send(
        self: Session, request: PreparedRequest, **kwargs: Any
    ):
        logger.debug(f"Instrumenting 'requests' request to {request.url}")
        _modify_request(request, context_f, logger)
        # Call original method
        return wrapped_send(self, request, **kwargs)

    # Apply wrapper
    Session.send = _send

def _modify_request(request, context_f: ExecContextF, logger):
    ctxt = context_f()

    headers = request.headers
    url = request.url
    hostname = _get_hostname(url)
    is_local_url = hostname.endswith(".local") or hostname.endswith(".minikube") or hostname.endswith(".ivcap.net")
    if not is_local_url:
        request.url = _wrap_proxy_url(url, headers)
    job_id = ctxt.job_id if ctxt != None else None
    if job_id != None: # OTEL messages won't have a jobID
        headers["Ivcap-Job-Id"] = job_id
    auth = ctxt.job_authorization if ctxt != None else None
    if auth != None and is_local_url:
        logger.debug(f"Adding 'Authorization' header")
        headers["Authorization"] = auth

def _get_hostname(url):
    try:
        if isinstance(url, URLx):
            return url.host
        if isinstance(url, str):
            return urlparse(url).hostname
    except Exception:
        return ""

ivcap_proxy_url = os.getenv('IVCAP_PROXY_URL')

def _wrap_proxy_url(url, headers):
    global ivcap_proxy_url
    if ivcap_proxy_url == None:
        return url

    if isinstance(url, URLx):
        # ensuring that any 'unset' query parameters are not included
        # in the final URL
        query_params = [(k, v) for k, v in url.params.items() if v is not None]
        url2 = URLx(url).copy_with(params=query_params)
        forward_url = str(url2)
        proxy_url = URLx(ivcap_proxy_url)
    if isinstance(url, str):
        forward_url = url # urllib.parse.quote_plus(url)
        proxy_url = ivcap_proxy_url
    headers["Ivcap-Forward-Url"] = forward_url
    return proxy_url

def extend_httpx(context_f: ExecContextF):
    try:
        import httpx
    except ImportError:
        return

    logger = getLogger("app.httpx")

    # Save original function
    wrapped_send = httpx.Client.send
    def _send(self, request, **kwargs):
        logger.debug(f"Instrumenting 'httpx' request to {request.url}")
        _modify_request(request, context_f, logger)
        # Call original method
        return wrapped_send(self, request, **kwargs)
    # Apply wrapper
    httpx.Client.send = _send

    wrapped_asend = httpx.AsyncClient.send
    def _asend(self, request, **kwargs):
        logger.debug(f"Instrumenting 'httpx' async request to {request.url}")
        _modify_request(request, context_f, logger)
        return wrapped_asend(self, request, **kwargs)
    httpx.AsyncClient.send = _asend

def set_context(context_f: ExecContextF):
    extend_requests(context_f)
    extend_httpx(context_f)