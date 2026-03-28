#
# Copyright (c) 2025 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#

# Various "patches" to maiontain context between incoming requests
# and calls to external services within a "session"
#
import functools
import os
from collections.abc import Callable
from logging import Logger
from typing import Any, cast
from urllib.parse import urlparse

from httpx import URL as URLx

from ivcap_service import getLogger

from .types import JobContext

ExecContextF = Callable[[], JobContext | None]


def otel_instrument(
    with_telemetry: bool | None,
    extension: Callable[[str], None] | None,
    logger: Logger,
):
    if not with_telemetry:
        return
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if endpoint is None:
        # `with_telemetry` can only be `True` or `None` based on its type.
        if with_telemetry:
            logger.warning("requested --with-telemetry but exporter is not defined")
        return

    if os.environ.get("PYTHONPATH") is None:
        os.environ["PYTHONPATH"] = ""
    logger.info(f"instrumenting for endpoint {endpoint}")
    if extension is not None:
        extension(endpoint)
    # Also instrumemt
    try:
        from opentelemetry.instrumentation.requests import RequestsInstrumentor

        RequestsInstrumentor().instrument()
    except ImportError:
        pass
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
    except ImportError:
        pass


def extend_requests(context_f: ExecContextF):
    from requests import PreparedRequest, Session

    logger = getLogger("app.request")

    # Save original function
    wrapped_send = Session.send

    @functools.wraps(wrapped_send)
    def _send(self: Session, request: PreparedRequest, **kwargs: Any):
        ctxt = context_f()
        logger.debug(
            f"{ctxt.job_id if ctxt else '???'}: Instrumenting 'requests' request to {request.url}"
        )
        _modify_request(request, ctxt, logger)
        # Call original method
        return wrapped_send(self, request, **kwargs)

    # Apply wrapper
    Session.send = _send


def _modify_request(request: Any, ctxt: JobContext | None, logger: Logger):
    headers = request.headers
    url = cast(URLx | str, request.url)
    hostname: str = _get_hostname(url)
    is_local_url = (
        hostname.endswith(".local")
        or hostname.endswith(".minikube")
        or hostname.endswith(".ivcap.net")
    )
    if not is_local_url:
        (request.url, is_local_url) = _wrap_proxy_url(url, headers, logger)
    job_id = ctxt.job_id if ctxt is not None else None
    if job_id is not None:  # OTEL messages won't have a jobID
        headers["Ivcap-Job-Id"] = job_id
    auth = ctxt.job_authorization if ctxt is not None else None
    if auth is not None and is_local_url:
        logger.debug(f"Adding 'Authorization' header to `{request.url}'")
        headers["Authorization"] = auth


def _get_hostname(url: URLx | str) -> str:
    try:
        if isinstance(url, URLx):
            return url.host or ""
        if isinstance(url, str):
            return urlparse(url).hostname or ""
    except Exception:
        return ""
    return ""


ivcap_proxy_url = os.getenv("IVCAP_PROXY_URL")


def _wrap_proxy_url(url, headers, logger):
    global ivcap_proxy_url
    if ivcap_proxy_url is None:
        return (url, False)

    if isinstance(url, URLx):
        # ensuring that any 'unset' query parameters are not included
        # in the final URL
        query_params = [(k, v) for k, v in url.params.items() if v is not None]
        url2 = URLx(url).copy_with(params=query_params)
        forward_url = str(url2)
        proxy_url = URLx(ivcap_proxy_url)
    if isinstance(url, str):
        forward_url = url  # urllib.parse.quote_plus(url)
        proxy_url = ivcap_proxy_url
    headers["Ivcap-Forward-Url"] = forward_url
    logger.debug(f"Rerouting external '{forward_url}' to '{ivcap_proxy_url}'")
    return (proxy_url, True)


def extend_httpx(context_f: ExecContextF):
    try:
        import httpx
    except ImportError:
        return

    logger = getLogger("app.httpx")

    # NOTE: we intentionally keep this wrapper untyped (Any) since httpx's
    # `Client.send` signature is complex and changes between versions.
    # This is still runtime-safe, but keeps Pyright happy in basic mode.
    wrapped_send = httpx.Client.send

    def _send(self: Any, request: Any, **kwargs: Any):
        ctxt = context_f()
        logger.debug(
            f"{ctxt.job_id if ctxt else '???'}: Instrumenting 'httpx' request to {request.url}"
        )
        _modify_request(request, ctxt, logger)
        return wrapped_send(self, request, **kwargs)

    httpx.Client.send = cast(Any, _send)

    wrapped_asend = httpx.AsyncClient.send

    def _asend(self: Any, request: Any, **kwargs: Any):
        ctxt = context_f()
        logger.debug(
            f"{ctxt.job_id if ctxt else '???'}: Instrumenting 'httpx' async request to {request.url}"
        )
        _modify_request(request, ctxt, logger)
        return wrapped_asend(self, request, **kwargs)

    httpx.AsyncClient.send = cast(Any, _asend)


def set_context(context_f: ExecContextF):
    extend_requests(context_f)
    extend_httpx(context_f)
