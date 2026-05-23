import pytest

from ivcap_service.openobserve import load_openobserve_config_from_env


def test_openobserve_disabled_without_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENOBSERVE_URL", raising=False)
    monkeypatch.delenv("OPENOBSERVE_OTLP_ENDPOINT", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.delenv("OPENOBSERVE_ENABLED", raising=False)
    cfg = load_openobserve_config_from_env(service_name="svc", service_version="1")
    assert cfg is None


def test_openobserve_endpoint_derived_from_url(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENOBSERVE_URL", "https://observe.example.com")
    monkeypatch.setenv("OPENOBSERVE_ORG", "acme")
    monkeypatch.setenv("OPENOBSERVE_USERNAME", "svc@example.com")
    monkeypatch.setenv("OPENOBSERVE_TOKEN", "t0k")
    cfg = load_openobserve_config_from_env(service_name="svc")
    assert cfg is not None
    assert cfg.endpoint == "https://observe.example.com/api/acme"
    assert cfg.use_unified_otlp_endpoint is False
    assert cfg.logs_endpoint() == "https://observe.example.com/api/acme/v1/logs"
    assert cfg.metrics_endpoint() == "https://observe.example.com/api/acme/v1/metrics"
    assert cfg.traces_endpoint() == "https://observe.example.com/api/acme/v1/traces"
    assert cfg.logs_headers()["stream-name"] == "default"
    assert cfg.headers["Authorization"].startswith("Basic ")


def test_openobserve_otel_endpoint_wins(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENOBSERVE_URL", "https://observe.example.com")
    monkeypatch.setenv("OPENOBSERVE_ORG", "acme")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_HEADERS", "x=a,Authorization=Bearer z")
    cfg = load_openobserve_config_from_env()
    assert cfg is not None
    assert cfg.endpoint == "http://collector:4318"
    assert cfg.use_unified_otlp_endpoint is False
    assert cfg.headers["x"] == "a"
    assert cfg.headers["Authorization"] == "Bearer z"


def test_openobserve_explicit_enabled_requires_endpoint(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("OPENOBSERVE_ENABLED", "true")
    monkeypatch.delenv("OPENOBSERVE_URL", raising=False)
    monkeypatch.delenv("OPENOBSERVE_OTLP_ENDPOINT", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    with pytest.raises(ValueError):
        load_openobserve_config_from_env()


def test_openobserve_rejects_endpoint_without_scheme(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENOBSERVE_ENABLED", "true")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "collector:4318")
    with pytest.raises(ValueError, match=r"http://|https://"):
        load_openobserve_config_from_env()


def test_openobserve_rejects_endpoint_without_hostname(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENOBSERVE_ENABLED", "true")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://:4318")
    with pytest.raises(ValueError, match=r"hostname"):
        load_openobserve_config_from_env()


def test_openobserve_signal_specific_endpoints(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENOBSERVE_URL", "https://observe.example.com")
    monkeypatch.setenv("OPENOBSERVE_ORG", "acme")
    monkeypatch.setenv("OPENOBSERVE_USERNAME", "svc@example.com")
    monkeypatch.setenv("OPENOBSERVE_TOKEN", "t0k")
    cfg = load_openobserve_config_from_env(service_name="svc")
    assert cfg is not None
    # OpenObserve default: signal-specific endpoints + stream-name header
    assert cfg.use_unified_otlp_endpoint is False
    assert cfg.logs_endpoint().endswith("/v1/logs")
    assert cfg.metrics_endpoint().endswith("/v1/metrics")
    assert cfg.logs_headers()["stream-name"] == "default"
    assert cfg.metrics_headers()["stream-name"] == "default"
    assert cfg.traces_headers()["stream-name"] == "default"

    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318")
    cfg2 = load_openobserve_config_from_env(service_name="svc")
    assert cfg2 is not None
    # Standard OTLP uses signal-specific paths
    assert cfg2.use_unified_otlp_endpoint is False
    assert cfg2.logs_endpoint() == "http://collector:4318/v1/logs"
    assert cfg2.metrics_endpoint() == "http://collector:4318/v1/metrics"


def test_openobserve_explicit_endpoint_without_v1_otlp(monkeypatch: pytest.MonkeyPatch):
    """Regression: OpenObserve base endpoint should be normalised to /api/<org>."""

    monkeypatch.setenv(
        "OPENOBSERVE_OTLP_ENDPOINT", "https://observe.example.com/api/acme"
    )
    monkeypatch.setenv("OPENOBSERVE_USERNAME", "svc@example.com")
    monkeypatch.setenv("OPENOBSERVE_TOKEN", "t0k")
    cfg = load_openobserve_config_from_env(service_name="svc")
    assert cfg is not None
    assert cfg.use_unified_otlp_endpoint is False
    assert cfg.logs_endpoint() == "https://observe.example.com/api/acme/v1/logs"
    assert cfg.metrics_endpoint() == "https://observe.example.com/api/acme/v1/metrics"


def test_openobserve_explicit_unified_endpoint(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENOBSERVE_URL", "https://observe.example.com")
    monkeypatch.setenv("OPENOBSERVE_ORG", "acme")
    monkeypatch.setenv("OPENOBSERVE_USERNAME", "svc@example.com")
    monkeypatch.setenv("OPENOBSERVE_TOKEN", "t0k")
    monkeypatch.setenv("OPENOBSERVE_USE_UNIFIED_OTLP_ENDPOINT", "true")
    cfg = load_openobserve_config_from_env(service_name="svc")
    assert cfg is not None
    assert cfg.use_unified_otlp_endpoint is True
    assert cfg.logs_endpoint().endswith("/v1/otlp")
    assert cfg.metrics_endpoint().endswith("/v1/otlp")
    assert cfg.traces_endpoint().endswith("/v1/otlp")


def test_openobserve_token_requires_username(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENOBSERVE_URL", "https://observe.example.com")
    monkeypatch.setenv("OPENOBSERVE_ORG", "acme")
    monkeypatch.setenv("OPENOBSERVE_TOKEN", "t0k")
    monkeypatch.delenv("OPENOBSERVE_USERNAME", raising=False)

    # If either USERNAME or TOKEN is defined, both must be present. (If you are
    # relying on a proxy injecting auth, leave both unset.)
    with pytest.raises(ValueError, match=r"USERNAME.*TOKEN|TOKEN.*USERNAME"):
        load_openobserve_config_from_env(service_name="svc")


def test_openobserve_url_without_creds_is_ok(monkeypatch: pytest.MonkeyPatch):
    """Proxy-injected auth scenario: endpoint configured but no creds provided."""

    monkeypatch.setenv("OPENOBSERVE_URL", "https://observe.example.com")
    monkeypatch.setenv("OPENOBSERVE_ORG", "acme")
    monkeypatch.delenv("OPENOBSERVE_USERNAME", raising=False)
    monkeypatch.delenv("OPENOBSERVE_TOKEN", raising=False)
    monkeypatch.delenv("OPENOBSERVE_PASSWORD", raising=False)
    cfg = load_openobserve_config_from_env(service_name="svc")
    assert cfg is not None
    assert "Authorization" not in cfg.headers


def test_openobserve_username_without_token_or_password_complains(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("OPENOBSERVE_URL", "https://observe.example.com")
    monkeypatch.setenv("OPENOBSERVE_ORG", "acme")
    monkeypatch.setenv("OPENOBSERVE_USERNAME", "svc@example.com")
    monkeypatch.delenv("OPENOBSERVE_TOKEN", raising=False)
    monkeypatch.delenv("OPENOBSERVE_PASSWORD", raising=False)
    with pytest.raises(ValueError, match=r"USERNAME.*TOKEN|TOKEN.*USERNAME"):
        load_openobserve_config_from_env(service_name="svc")
