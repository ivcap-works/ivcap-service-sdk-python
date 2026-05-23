#
# Copyright (c) 2026 Commonwealth Scientific and Industrial Research Organisation (CSIRO).
# All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
"""OpenObserve reporting (logs + metrics) via OpenTelemetry OTLP/HTTP.

This module is intentionally **opt-in** and is configured primarily through
environment variables.

## Environment variables

OpenObserve-specific variables (preferred for convenience):

* `OPENOBSERVE_URL`               Base URL, e.g. `https://observe.example.com`
* `OPENOBSERVE_ORG`               Org name (default: `default`)
* `OPENOBSERVE_OTLP_ENDPOINT`     Full OTLP endpoint URL (overrides derived URL)
* `OPENOBSERVE_AUTH`              Full value for the `Authorization` header
* `OPENOBSERVE_TOKEN`             Convenience: combined with `OPENOBSERVE_USERNAME` into
                                 `Authorization: Basic <base64(user:token)>`.
                                 (If you need a Bearer token, use `OPENOBSERVE_AUTH`.)
* `OPENOBSERVE_USERNAME` / `OPENOBSERVE_PASSWORD`
                                 Convenience: sets HTTP Basic auth header
* `OPENOBSERVE_ENABLE_LOGS`       Enable log exporting (default: true)
* `OPENOBSERVE_ENABLE_METRICS`    Enable metric exporting (default: true)
* `OPENOBSERVE_METRICS_INTERVAL`  Export interval in seconds (default: 60)
* `OPENOBSERVE_LOGS_STREAM_NAME`  Stream name for logs (default: `default`)
* `OPENOBSERVE_METRICS_STREAM_NAME`
                                 Stream name for metrics (default: `default`)
* `OPENOBSERVE_ADD_STREAM_NAME_HEADER`
                                 Add `stream-name` header (default: true)
* `OPENOBSERVE_USE_UNIFIED_OTLP_ENDPOINT`
                                 Use unified `/v1/otlp` endpoint (default: false)

Standard OpenTelemetry variables can still be used to override details, such as:

* `OTEL_EXPORTER_OTLP_ENDPOINT`
* `OTEL_EXPORTER_OTLP_HEADERS`

Resolution order:

1. If `OTEL_EXPORTER_OTLP_ENDPOINT` is set, it wins.
2. Else if `OPENOBSERVE_OTLP_ENDPOINT` is set, it wins.
3. Else derive endpoint from `OPENOBSERVE_URL` (+ `OPENOBSERVE_ORG`).

This means OpenObserve config provides convenient defaults while remaining
compatible with common OTEL env configuration patterns.
"""

from __future__ import annotations

import base64
import logging
import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlparse


def _is_truthy(v: str | None, *, default: bool = False) -> bool:
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "on")


def _parse_kv_list(value: str | None) -> dict[str, str]:
    """Parse OTEL header env format: `k=v,k2=v2` (commas or semicolons)."""

    if value is None:
        return {}
    out: dict[str, str] = {}
    for part in value.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            # best-effort: ignore malformed fragments
            continue
        k, v = part.split("=", 1)
        k = k.strip()
        v = v.strip()
        if k:
            out[k] = v
    return out


def _normalize_openobserve_auth(*, auth: str, username: str | None = None) -> str:
    """Best-effort normalisation of OpenObserve auth.

    OpenObserve OTLP ingestion commonly expects:
      Authorization: Basic <base64(user:password)>

    Operators may provide:
    - "Basic <base64>" (recommended)
    - "Bearer <token>" (some setups)
    - "<base64>" (missing scheme)
    - "user:password" (raw credentials)
    - "<token>" (service account token; treat as password if username present)
    """

    a = (auth or "").strip().strip('"')
    if not a:
        return ""

    lower = a.lower()
    if lower.startswith("basic ") or lower.startswith("bearer "):
        return a

    # raw credentials
    if ":" in a:
        b64 = base64.b64encode(a.encode("utf-8")).decode("ascii")
        return f"Basic {b64}"

    # maybe they provided the base64 part only
    try:
        dec = base64.b64decode(a, validate=True).decode("utf-8", errors="ignore")
        if ":" in dec:
            return f"Basic {a}"
    except Exception:
        pass

    # treat token as "password" with provided username
    if username:
        b64 = base64.b64encode(f"{username}:{a}".encode()).decode("ascii")
        return f"Basic {b64}"

    # Unknown format; return as-is.
    return a


def _urlenc(v: str) -> str:
    """URL-encode a header value for OTEL env compatibility."""

    return quote(v, safe="")


@dataclass(frozen=True)
class OpenObserveConfig:
    enabled: bool

    # Export destination
    endpoint: str
    headers: dict[str, str]

    # Signals
    enable_logs: bool
    enable_metrics: bool
    enable_traces: bool
    metrics_interval_seconds: float

    # Endpoint behaviour
    #
    # OpenObserve OTLP/HTTP commonly uses signal-specific endpoints at:
    #   .../api/<org>/v1/logs
    #   .../api/<org>/v1/metrics
    #
    # Some deployments/docs also mention a unified endpoint:
    #   .../api/<org>/v1/otlp
    #
    # We keep this as an explicit flag because OpenTelemetry exporters do not
    # add paths when an explicit `endpoint=` is supplied.
    #
    # Default: when configuring via OPENOBSERVE_* we use signal-specific paths
    # (more compatible with current OpenObserve docs/examples).
    use_unified_otlp_endpoint: bool = False

    # Optional OpenObserve stream routing
    #
    # OpenObserve can use `stream-name` header to route signals. If set,
    # we will add it (per signal) when using OpenObserve endpoints.
    logs_stream_name: str | None = None
    metrics_stream_name: str | None = None
    traces_stream_name: str | None = None

    # Resource metadata
    service_name: str | None = None
    service_version: str | None = None

    def logs_endpoint(self) -> str:
        """Return an OTLP/HTTP endpoint appropriate for log exporting.

        Notes:
        * OpenObserve supports a single `/v1/otlp` endpoint for all signals.
        * Standard OTLP/HTTP expects `/v1/logs`.
        """

        if self.use_unified_otlp_endpoint:
            return _openobserve_unified_endpoint(self.endpoint)
        # Prefer OpenObserve-style endpoints when `endpoint` looks like an
        # OpenObserve base.
        if _looks_like_openobserve_base(self.endpoint):
            return _openobserve_signal_endpoint(self.endpoint, "logs")
        return _signal_endpoint(self.endpoint, "logs")

    def metrics_endpoint(self) -> str:
        """Return an OTLP/HTTP endpoint appropriate for metric exporting."""

        if self.use_unified_otlp_endpoint:
            return _openobserve_unified_endpoint(self.endpoint)
        if _looks_like_openobserve_base(self.endpoint):
            return _openobserve_signal_endpoint(self.endpoint, "metrics")
        return _signal_endpoint(self.endpoint, "metrics")

    def logs_headers(self) -> dict[str, str]:
        h = dict(self.headers)
        if self.logs_stream_name and "stream-name" not in h:
            h["stream-name"] = self.logs_stream_name
        return h

    def metrics_headers(self) -> dict[str, str]:
        h = dict(self.headers)
        if self.metrics_stream_name and "stream-name" not in h:
            h["stream-name"] = self.metrics_stream_name
        return h

    def traces_endpoint(self) -> str:
        """Return an OTLP/HTTP endpoint appropriate for trace exporting."""

        if self.use_unified_otlp_endpoint:
            return _openobserve_unified_endpoint(self.endpoint)
        if _looks_like_openobserve_base(self.endpoint):
            return _openobserve_signal_endpoint(self.endpoint, "traces")
        return _signal_endpoint(self.endpoint, "traces")

    def traces_headers(self) -> dict[str, str]:
        h = dict(self.headers)
        if self.traces_stream_name and "stream-name" not in h:
            h["stream-name"] = self.traces_stream_name
        return h


def _openobserve_unified_endpoint(endpoint: str) -> str:
    """Return an OpenObserve compatible OTLP/HTTP ingest endpoint.

    OpenObserve expects `/v1/otlp` for all signals. Users sometimes configure an
    endpoint at the OpenObserve org base, e.g. `.../api/<org>`.
    """

    ep = endpoint.rstrip("/")
    if ep.endswith("/v1/otlp"):
        return endpoint
    if ep.endswith("/v1"):
        return f"{ep}/otlp"
    return f"{ep}/v1/otlp"


def _looks_like_openobserve_base(endpoint: str) -> bool:
    # Heuristic: OpenObserve org base endpoints typically include `/api/<org>`.
    # We also treat anything that ends with `/api/<org>` or `/api/<org>/` as a base.
    ep = endpoint.rstrip("/")
    return "/api/" in ep and not ep.endswith("/v1/otlp")


def _openobserve_signal_endpoint(endpoint: str, signal: str) -> str:
    ep = endpoint.rstrip("/")
    # If a user provides an endpoint already pointing at /v1/<signal>, keep it.
    for sfx in ("/v1/logs", "/v1/metrics", "/v1/traces"):
        if ep.endswith(sfx):
            return endpoint
    # If they provided /v1/otlp, keep it.
    if ep.endswith("/v1/otlp"):
        return endpoint
    return f"{ep}/v1/{signal}"


def _validate_otlp_http_endpoint(endpoint: str) -> str:
    endpoint = endpoint.strip()
    if endpoint == "":
        raise ValueError("OTLP endpoint is empty")

    p = urlparse(endpoint)
    if p.scheme not in ("http", "https"):
        raise ValueError(
            f"OTLP endpoint must start with http:// or https:// (got: {endpoint!r})"
        )
    if not p.hostname:
        # This catches things like http://:4318
        raise ValueError(f"OTLP endpoint must include a hostname (got: {endpoint!r})")
    return endpoint


def _signal_endpoint(endpoint: str, signal: str) -> str:
    """Derive a signal-specific OTLP/HTTP endpoint.

    If the endpoint already targets a known OTLP path, it is returned unchanged.
    Otherwise, `/v1/<signal>` is appended.
    """

    ep = endpoint.rstrip("/")
    # OpenObserve unified endpoint
    if ep.endswith("/v1/otlp"):
        return endpoint

    # Already signal-specific
    for sfx in ("/v1/logs", "/v1/metrics", "/v1/traces"):
        if ep.endswith(sfx):
            return endpoint

    return f"{ep}/v1/{signal}"


def load_openobserve_config_from_env(
    *,
    service_name: str | None = None,
    service_version: str | None = None,
) -> OpenObserveConfig | None:
    """Build an OpenObserve config from environment variables.

    Returns `None` if there isn't enough configuration to enable OpenObserve.
    """

    enable_logs = _is_truthy(os.getenv("OPENOBSERVE_ENABLE_LOGS"), default=True)
    enable_metrics = _is_truthy(os.getenv("OPENOBSERVE_ENABLE_METRICS"), default=True)
    enable_traces = _is_truthy(os.getenv("OPENOBSERVE_ENABLE_TRACES"), default=True)

    # Allow explicit enable/disable switch, but also enable implicitly when a
    # destination is configured.
    explicit_enabled = os.getenv("OPENOBSERVE_ENABLED")
    enabled = _is_truthy(explicit_enabled, default=False) if explicit_enabled else None

    otel_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    oo_endpoint = os.getenv("OPENOBSERVE_OTLP_ENDPOINT")
    oo_url = os.getenv("OPENOBSERVE_URL")
    oo_org = os.getenv("OPENOBSERVE_ORG") or "default"
    oo_use_unified = _is_truthy(
        os.getenv("OPENOBSERVE_USE_UNIFIED_OTLP_ENDPOINT"), default=False
    )
    oo_add_stream_header = _is_truthy(
        os.getenv("OPENOBSERVE_ADD_STREAM_NAME_HEADER"), default=True
    )

    # If the endpoint originates from OpenObserve config (URL or explicit
    # OPENOBSERVE_OTLP_ENDPOINT), we default to OpenObserve signal-specific
    # endpoints:
    #   .../api/<org>/v1/logs
    #   .../api/<org>/v1/metrics
    #
    # If it comes from OTEL_EXPORTER_OTLP_ENDPOINT, we default to standard
    # signal-specific paths (/v1/logs, /v1/metrics).
    endpoint_source: str | None = None

    endpoint = None
    if otel_endpoint not in (None, ""):
        endpoint = otel_endpoint
        endpoint_source = "otel"
    elif oo_endpoint not in (None, ""):
        endpoint = oo_endpoint
        endpoint_source = "openobserve"
        # Normalise to OpenObserve org base by default.
        ep = endpoint.rstrip("/")
        for sfx in ("/v1/logs", "/v1/metrics", "/v1/traces"):
            if ep.endswith(sfx):
                endpoint = ep[: -len(sfx)]
                break
        # If user supplied /v1/otlp, treat it as base unless unified is requested.
        if endpoint.rstrip("/").endswith("/v1/otlp") and not oo_use_unified:
            endpoint = endpoint.rstrip("/")[: -len("/v1/otlp")]
    elif oo_url not in (None, ""):
        endpoint = f"{oo_url.rstrip('/')}/api/{oo_org}"
        endpoint_source = "openobserve"

    if endpoint in (None, ""):
        # nothing configured => no-op
        if enabled is True:
            # user explicitly asked, but we can't do it
            raise ValueError(
                "OPENOBSERVE_ENABLED is true but no endpoint configured; set OPENOBSERVE_URL, OPENOBSERVE_OTLP_ENDPOINT or OTEL_EXPORTER_OTLP_ENDPOINT"
            )
        return None

    # Validate URL early so we don't end up with noisy exporter thread errors.
    # Examples of invalid endpoints which otherwise lead to `socket.gaierror`:
    #   - "http://:4318" (missing hostname)
    #   - "collector:4318" (missing scheme)
    endpoint = _validate_otlp_http_endpoint(endpoint)

    # If user didn't explicitly enable/disable, enable if any OpenObserve env is present.
    if enabled is None:
        enabled = any(
            os.getenv(k) not in (None, "")
            for k in (
                "OPENOBSERVE_URL",
                "OPENOBSERVE_OTLP_ENDPOINT",
                "OPENOBSERVE_TOKEN",
                "OPENOBSERVE_AUTH",
                "OPENOBSERVE_USERNAME",
            )
        )

    if not enabled:
        return None

    # Headers: start with OTEL headers, allow OpenObserve-specific overrides.
    headers = _parse_kv_list(os.getenv("OTEL_EXPORTER_OTLP_HEADERS"))
    headers.update(_parse_kv_list(os.getenv("OPENOBSERVE_HEADERS")))

    # Convenience auth helpers.
    if "Authorization" not in headers:
        auth = os.getenv("OPENOBSERVE_AUTH")
        if auth not in (None, ""):
            headers["Authorization"] = auth
        else:
            token = os.getenv("OPENOBSERVE_TOKEN")
            user = os.getenv("OPENOBSERVE_USERNAME")
            pwd = os.getenv("OPENOBSERVE_PASSWORD")

            token_set = token not in (None, "")
            user_set = user not in (None, "")
            pwd_set = pwd not in (None, "")

            # If one of TOKEN/USERNAME is set but not the other, this is almost
            # always a misconfiguration.
            #
            # If you intend to rely on a reverse proxy injecting auth in-flight,
            # leave *both* OPENOBSERVE_USERNAME and OPENOBSERVE_TOKEN unset.
            #
            # If you intend to provide a full auth header (Bearer/Basic), use
            # OPENOBSERVE_AUTH (or OTEL_EXPORTER_OTLP_HEADERS).
            if token_set and not user_set:
                raise ValueError(
                    "OPENOBSERVE_USERNAME and OPENOBSERVE_TOKEN must be set together (or neither). "
                    "If OpenObserve is behind a proxy that injects auth, leave both unset. "
                    "Otherwise, set both (Basic user:token) or provide OPENOBSERVE_AUTH."
                )

            if user_set and (not token_set) and (not pwd_set):
                raise ValueError(
                    "OPENOBSERVE_USERNAME and OPENOBSERVE_TOKEN must be set together (or neither). "
                    "If OpenObserve is behind a proxy that injects auth, leave both unset. "
                    "Otherwise, set both (Basic user:token) or provide OPENOBSERVE_AUTH."
                )

            if token_set and user_set:
                headers["Authorization"] = _normalize_openobserve_auth(
                    auth=token or "", username=user
                )
            elif user_set and pwd_set:
                raw = f"{user}:{pwd}".encode()
                headers["Authorization"] = "Basic " + base64.b64encode(raw).decode(
                    "ascii"
                )

    logs_stream_name = None
    metrics_stream_name = None
    traces_stream_name = None
    if endpoint_source == "openobserve" and oo_add_stream_header:
        logs_stream_name = os.getenv("OPENOBSERVE_LOGS_STREAM_NAME") or "default"
        metrics_stream_name = os.getenv("OPENOBSERVE_METRICS_STREAM_NAME") or "default"
        traces_stream_name = os.getenv("OPENOBSERVE_TRACES_STREAM_NAME") or "default"

    interval_s = os.getenv("OPENOBSERVE_METRICS_INTERVAL")
    try:
        metrics_interval_seconds = float(interval_s) if interval_s else 60.0
    except ValueError:
        metrics_interval_seconds = 60.0

    return OpenObserveConfig(
        enabled=True,
        endpoint=endpoint,
        headers=headers,
        enable_logs=enable_logs,
        enable_metrics=enable_metrics,
        enable_traces=enable_traces,
        metrics_interval_seconds=metrics_interval_seconds,
        use_unified_otlp_endpoint=(endpoint_source == "openobserve" and oo_use_unified),
        logs_stream_name=logs_stream_name,
        metrics_stream_name=metrics_stream_name,
        traces_stream_name=traces_stream_name,
        service_name=service_name,
        service_version=service_version,
    )


def init_openobserve_from_env(
    *,
    logger: logging.Logger | None = None,
    service_name: str | None = None,
    service_version: str | None = None,
) -> OpenObserveConfig | None:
    """Initialise OpenTelemetry exporters for OpenObserve (logs + metrics).

    Safe to call multiple times; initialisation is idempotent.
    """

    try:
        cfg = load_openobserve_config_from_env(
            service_name=service_name, service_version=service_version
        )
    except Exception as e:
        if logger is None:
            logger = logging.getLogger("openobserve")
        logger.warning("OpenObserve config invalid; disabling exporters: %s", e)
        return None
    if cfg is None:
        return None

    if logger is None:
        logger = logging.getLogger("openobserve")

    # Helpful diagnostics for common OpenObserve misconfigurations.
    try:
        auth = cfg.headers.get("Authorization")
        if (
            auth
            and auth.strip().lower().startswith("bearer ")
            and os.getenv("OPENOBSERVE_USERNAME") in (None, "")
        ):
            logger.warning(
                "OpenObserve OTLP auth is configured as Bearer token. Many OpenObserve deployments expect Basic auth (base64(user:password)). "
                "Consider setting OPENOBSERVE_USERNAME (and OPENOBSERVE_TOKEN as password) or set OPENOBSERVE_AUTH to a full 'Basic ...' header value."
            )
    except Exception:
        pass

    def _redact_headers(h: dict[str, str]) -> dict[str, str]:
        out = dict(h)
        if "Authorization" in out:
            v = out["Authorization"]
            out["Authorization"] = v.split(" ", 1)[0] + " ***" if " " in v else "***"
        return out

    logger.info(
        "OpenObserve OTLP resolved endpoints: logs=%s metrics=%s unified=%s",
        cfg.logs_endpoint(),
        cfg.metrics_endpoint(),
        cfg.use_unified_otlp_endpoint,
    )
    logger.debug(
        "OpenObserve OTLP headers (logs)=%s (metrics)=%s",
        _redact_headers(cfg.logs_headers()),
        _redact_headers(cfg.metrics_headers()),
    )

    # Delayed imports to avoid hard dependency at import-time and to keep the
    # base SDK usable without OpenTelemetry installed.
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.semconv.resource import ResourceAttributes

    resource_attrs: dict[str, Any] = {}
    if cfg.service_name:
        resource_attrs[ResourceAttributes.SERVICE_NAME] = cfg.service_name
    if cfg.service_version:
        resource_attrs[ResourceAttributes.SERVICE_VERSION] = cfg.service_version
    resource = Resource.create(resource_attrs)

    if cfg.enable_logs:
        _init_logs(cfg, resource, logger)
        logger.info("OpenObserve log exporting enabled")
    else:
        logger.info("OpenObserve log exporting disabled by env")

    if cfg.enable_metrics:
        _init_metrics(cfg, resource, logger)
        logger.info(
            "OpenObserve metric exporting enabled (interval=%ss)",
            cfg.metrics_interval_seconds,
        )
    else:
        logger.info("OpenObserve metric exporting disabled by env")

    if cfg.enable_traces:
        _init_traces(cfg, resource, logger)
        logger.info("OpenObserve trace exporting enabled")
    else:
        logger.info("OpenObserve trace exporting disabled by env")

    return cfg


def _init_logs(cfg: OpenObserveConfig, resource: Any, logger: logging.Logger) -> None:
    from opentelemetry._logs import set_logger_provider
    from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

    # Don't install twice.
    root = logging.getLogger()
    if any(getattr(h, "_ivcap_openobserve", False) for h in root.handlers):
        return

    exporter = OTLPLogExporter(endpoint=cfg.logs_endpoint(), headers=cfg.logs_headers())
    provider = LoggerProvider(resource=resource)
    provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
    set_logger_provider(provider)

    handler = LoggingHandler(level=logging.NOTSET, logger_provider=provider)
    setattr(handler, "_ivcap_openobserve", True)
    root.addHandler(handler)

    # Make sure log records can flow. We do *not* change logger levels here.
    logger.debug("Installed OpenObserve OTLP log handler")


def _init_metrics(
    cfg: OpenObserveConfig, resource: Any, logger: logging.Logger
) -> None:
    from opentelemetry import metrics
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
        OTLPMetricExporter,
    )
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

    # Don't install twice.
    provider = metrics.get_meter_provider()
    if getattr(provider, "_ivcap_openobserve", False):
        return

    exporter = OTLPMetricExporter(
        endpoint=cfg.metrics_endpoint(), headers=cfg.metrics_headers()
    )
    reader = PeriodicExportingMetricReader(
        exporter,
        export_interval_millis=int(cfg.metrics_interval_seconds * 1000),
    )
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    setattr(provider, "_ivcap_openobserve", True)
    metrics.set_meter_provider(provider)
    logger.debug("Installed OpenObserve OTLP metric reader")


class RuntimeMetrics:
    """Minimal runtime metrics emitted by this SDK.

    These are intended as lightweight, always-available metrics when OTEL
    metrics export is enabled.
    """

    def __init__(self):
        from opentelemetry import metrics

        meter = metrics.get_meter("ivcap_service.runtime")
        self._jobs_total = meter.create_counter(
            name="ivcap.jobs_total",
            description="Number of jobs executed by the service runtime",
            unit="1",
        )
        self._job_duration = meter.create_histogram(
            name="ivcap.job_duration_seconds",
            description="Job execution duration",
            unit="s",
        )

    def record_job(self, *, duration_seconds: float, ok: bool, error_type: str | None):
        attrs: dict[str, Any] = {"ok": ok}
        if error_type:
            attrs["error_type"] = error_type
        self._jobs_total.add(1, attributes=attrs)
        self._job_duration.record(duration_seconds, attributes=attrs)


def maybe_create_runtime_metrics() -> RuntimeMetrics | None:
    """Create SDK runtime metrics instruments if a MeterProvider is configured."""

    try:
        from opentelemetry import metrics

        # If no SDK provider is installed, this is usually a NoOp provider.
        # We only create instruments if OpenObserve (or some other OTEL
        # MeterProvider) was installed.
        provider = metrics.get_meter_provider()
        if provider.__class__.__name__.lower().startswith("noop"):
            return None
        return RuntimeMetrics()
    except Exception:
        return None


def _init_traces(cfg: OpenObserveConfig, resource: Any, logger: logging.Logger) -> None:
    """Initialise an OTLP/HTTP trace exporter.

    Note: We keep this separate from `otel_instrument()`; this is about exporting
    *SDK-created* spans (like job spans).
    """

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = trace.get_tracer_provider()
    if getattr(provider, "_ivcap_openobserve", False):
        return

    exporter = OTLPSpanExporter(
        endpoint=cfg.traces_endpoint(),
        headers=cfg.traces_headers(),
    )

    tp = TracerProvider(resource=resource)
    tp.add_span_processor(BatchSpanProcessor(exporter))
    setattr(tp, "_ivcap_openobserve", True)
    trace.set_tracer_provider(tp)
    logger.debug("Installed OpenObserve OTLP trace exporter")
