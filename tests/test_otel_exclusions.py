#
# Copyright (c) 2026 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
"""Tests for OTEL URL exclusion functionality.

This module tests the `_build_excluded_urls()` function that prevents
self-referential tracing by excluding OTEL collector endpoints and
internal service URLs from instrumentation.
"""


def test_excluded_urls_with_no_endpoint():
    """Test that no URLs are excluded without an OTEL endpoint or env var."""
    from ivcap_service.context import _build_excluded_urls

    excluded = _build_excluded_urls(otel_endpoint=None)
    assert excluded is None


def test_excluded_urls_with_http_endpoint():
    """Test that HTTP endpoint is properly excluded."""
    from ivcap_service.context import _build_excluded_urls

    excluded = _build_excluded_urls(otel_endpoint="http://localhost:4318")
    assert excluded is not None
    assert "http://localhost*" in excluded


def test_excluded_urls_with_https_endpoint():
    """Test that HTTPS endpoint is properly excluded."""
    from ivcap_service.context import _build_excluded_urls

    excluded = _build_excluded_urls(otel_endpoint="https://otel.example.com:4318")
    assert excluded is not None
    assert "https://otel.example.com*" in excluded


def test_excluded_urls_with_endpoint_path():
    """Test that endpoint with path is handled correctly."""
    from ivcap_service.context import _build_excluded_urls

    excluded = _build_excluded_urls(
        otel_endpoint="https://observe.example.com/api/default/v1/traces"
    )
    assert excluded is not None
    # Should extract just the hostname
    assert "https://observe.example.com*" in excluded


def test_excluded_urls_with_env_var(monkeypatch):
    """Test that OTEL_EXPORTER_SKIP_URLS environment variable is respected."""
    from ivcap_service.context import _build_excluded_urls

    monkeypatch.setenv(
        "OTEL_EXPORTER_SKIP_URLS", "http://custom.example.com/*,https://other.com/*"
    )

    excluded = _build_excluded_urls(otel_endpoint=None)
    assert excluded is not None
    assert "http://custom.example.com/*" in excluded
    assert "https://other.com/*" in excluded


def test_excluded_urls_with_env_var_semicolon(monkeypatch):
    """Test that OTEL_EXPORTER_SKIP_URLS supports semicolon separators."""
    from ivcap_service.context import _build_excluded_urls

    monkeypatch.setenv("OTEL_EXPORTER_SKIP_URLS", "http://a.com/*;https://b.com/*")

    excluded = _build_excluded_urls(otel_endpoint=None)
    assert excluded is not None
    assert "http://a.com/*" in excluded
    assert "https://b.com/*" in excluded


def test_excluded_urls_combined(monkeypatch):
    """Test that endpoint and env var are combined."""
    from ivcap_service.context import _build_excluded_urls

    monkeypatch.setenv("OTEL_EXPORTER_SKIP_URLS", "http://custom.example.com/*")

    excluded = _build_excluded_urls(otel_endpoint="https://collector.example.com:4318")
    assert excluded is not None
    # Should include both endpoint and env var patterns
    assert "https://collector.example.com*" in excluded
    assert "http://custom.example.com/*" in excluded


def test_excluded_urls_empty_env_var_ignored(monkeypatch):
    """Test that empty OTEL_EXPORTER_SKIP_URLS is ignored."""
    from ivcap_service.context import _build_excluded_urls

    monkeypatch.setenv("OTEL_EXPORTER_SKIP_URLS", "")

    excluded = _build_excluded_urls(otel_endpoint=None)
    assert excluded is None


def test_excluded_urls_with_whitespace(monkeypatch):
    """Test that whitespace in OTEL_EXPORTER_SKIP_URLS is handled."""
    from ivcap_service.context import _build_excluded_urls

    monkeypatch.setenv(
        "OTEL_EXPORTER_SKIP_URLS", "  http://a.com/* , https://b.com/*  "
    )

    excluded = _build_excluded_urls(otel_endpoint=None)
    assert excluded is not None
    assert "http://a.com/*" in excluded
    assert "https://b.com/*" in excluded


def test_excluded_urls_format_csv():
    """Test that excluded URLs are properly formatted."""
    from ivcap_service.context import _build_excluded_urls

    excluded = _build_excluded_urls(otel_endpoint="http://localhost:4318")
    assert excluded is not None
    # Should be a string (possibly with commas if multiple patterns)
    assert isinstance(excluded, str)
    # If there are multiple patterns, they should be comma-separated
    if "," in excluded:
        parts = excluded.split(",")
        # Each part should be stripped
        for part in parts:
            assert part == part.strip()


def test_excluded_urls_with_invalid_endpoint():
    """Test that invalid endpoints don't crash the function."""
    from ivcap_service.context import _build_excluded_urls

    # Should not raise an exception with invalid endpoint
    excluded = _build_excluded_urls(otel_endpoint="not-a-valid-url")
    assert excluded is None


def test_excluded_urls_with_localhost_variants():
    """Test various localhost endpoint formats."""
    from ivcap_service.context import _build_excluded_urls

    test_cases = [
        "http://localhost:4318",
        "http://127.0.0.1:4318",
        "http://otel-collector:4318",
        "https://otel.example.com:4318",
    ]

    for endpoint in test_cases:
        excluded = _build_excluded_urls(otel_endpoint=endpoint)
        assert excluded is not None
        # Should always exclude the endpoint
        assert "*" in excluded


def test_no_excluded_urls_returns_none_on_clean_env():
    """Test that None is returned when there are no exclusions."""
    from ivcap_service.context import _build_excluded_urls

    excluded = _build_excluded_urls(otel_endpoint=None)
    # No endpoint and no env var means no exclusions
    assert excluded is None


def test_excluded_urls_no_duplicates():
    """Test that if the same pattern is added multiple times, it's not duplicated."""
    from ivcap_service.context import _build_excluded_urls

    # Even if someone sets the same endpoint that's already in defaults,
    # the function should handle it gracefully
    excluded = _build_excluded_urls(otel_endpoint="http://localhost:4318")
    assert excluded is not None
    # Count occurrences of a pattern
    parts = excluded.split(",")
    assert len(parts) == len(set(parts)), "Duplicate patterns found"
