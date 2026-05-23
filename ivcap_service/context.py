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

from .logger import getLogger
from .types import JobContext

ExecContextF = Callable[[], JobContext | None]


def _build_excluded_urls(otel_endpoint: str | None = None) -> str | None:
    """Build a list of URLs that should not be traced.

    This prevents self-referential tracing where HTTP calls to export traces/logs/metrics
    to the OTEL collector are themselves traced, creating circular dependencies.

    Returns a comma-separated string of URL patterns, or None if no exclusions.

    Excludes:
    - OTEL collector endpoints (if provided)
    - User-specified exclusions via OTEL_EXPORTER_SKIP_URLS environment variable
    """
    excluded = []

    # Add OTEL collector endpoint if provided
    if otel_endpoint:
        try:
            parsed = urlparse(otel_endpoint)
            if parsed.hostname:
                # Add the base hostname with wildcard to catch all paths
                excluded.append(f"{parsed.scheme}://{parsed.hostname}*")
        except Exception:
            pass

    # Add user-specified exclusions from environment variable
    user_exclusions = os.environ.get("OTEL_EXPORTER_SKIP_URLS")
    if user_exclusions:
        # Support comma or semicolon separators
        for pattern in user_exclusions.replace(";", ",").split(","):
            pattern = pattern.strip()
            if pattern:
                excluded.append(pattern)

    if not excluded:
        return None

    return ",".join(excluded)


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

    # Build the list of URLs to exclude from tracing
    excluded_urls = _build_excluded_urls(endpoint)
    if excluded_urls:
        logger.debug(f"excluding URLs from tracing: {excluded_urls}")

    # Also instrument HTTP libraries with URL exclusions
    try:
        from opentelemetry.instrumentation.requests import RequestsInstrumentor

        RequestsInstrumentor().instrument(excluded_urls=excluded_urls)
    except ImportError:
        pass
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument(excluded_urls=excluded_urls)
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
    Session.send = cast(Any, _send)


def _is_otel_endpoint(url: URLx | str) -> bool:
    """Check if a URL is an OTEL collector endpoint.

    Returns True if the URL matches the OTEL_EXPORTER_OTLP_ENDPOINT.
    """
    otel_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not otel_endpoint:
        return False

    try:
        url_str = str(url)
        otel_parsed = urlparse(otel_endpoint)
        url_parsed = urlparse(url_str)

        # Check if the hostnames match
        return otel_parsed.hostname == url_parsed.hostname
    except Exception:
        return False


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
    # Don't add authorization to OTEL collector endpoints
    if auth is not None and is_local_url and not _is_otel_endpoint(url):
        logger.debug(f"Adding 'Authorization' header to `{request.url}'")
        headers["Authorization"] = auth


def _get_hostname(url: URLx | str) -> str:
    try:
        # We intentionally avoid accessing `httpx.URL.host` here to keep static
        # type checkers happy across httpx versions / stubs.
        return urlparse(str(url)).hostname or ""
    except Exception:
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
