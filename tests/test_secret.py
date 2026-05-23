#
# Copyright (c) 2026 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
import os

import pytest
import requests

from ivcap_service import get_secret
from ivcap_service.secret import SecretMgrClient


def test_secret_from_env():
    os.environ["MY_TEST_SECRET"] = "supersecretvalue"
    secret = get_secret("MY_TEST_SECRET")
    assert secret == "supersecretvalue"


def test_secret_from_env_not_overwritten():
    """Test that existing env variable is not overwritten."""
    os.environ["EXISTING_SECRET"] = "original_value"
    secret = get_secret("EXISTING_SECRET")
    assert secret == "original_value"
    assert os.environ["EXISTING_SECRET"] == "original_value"


def test_secret_mgr_client_default_url(monkeypatch: pytest.MonkeyPatch):
    """Test SecretMgrClient uses default URL when not set."""
    monkeypatch.delenv("SECRETMGR_PROXY", raising=False)
    client = SecretMgrClient()
    assert client.secret_url == "http://secretmgr.local"


def test_secret_mgr_client_custom_url(monkeypatch: pytest.MonkeyPatch):
    """Test SecretMgrClient accepts custom URL."""
    client = SecretMgrClient(secret_url="http://custom-secret-manager:9000")
    assert client.secret_url == "http://custom-secret-manager:9000"


def test_secret_mgr_client_env_url(monkeypatch: pytest.MonkeyPatch):
    """Test SecretMgrClient uses SECRETMGR_PROXY env variable."""
    monkeypatch.setenv("SECRETMGR_PROXY", "https://secret-proxy.example.com")
    client = SecretMgrClient()
    assert client.secret_url == "https://secret-proxy.example.com"


def test_secret_mgr_client_empty_secret_name():
    """Test SecretMgrClient rejects empty secret names."""
    client = SecretMgrClient()
    with pytest.raises(ValueError, match="empty secret name"):
        client.get_secret(secret_name="  ")


def test_secret_mgr_client_strips_secret_name():
    """Test SecretMgrClient strips whitespace from secret name."""
    client = SecretMgrClient()
    # Mock the requests.get to verify the correct name is used
    import unittest.mock

    with unittest.mock.patch("ivcap_service.secret.requests.get") as mock_get:
        mock_response = unittest.mock.MagicMock()
        mock_response.json.return_value = {"secret-value": "test123"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = client.get_secret(secret_name="  MY_SECRET  ")
        assert result == "test123"
        # Verify the call was made with the stripped name
        call_args = mock_get.call_args
        assert call_args[1]["params"]["secret-name"] == "MY_SECRET"


def test_secret_mgr_client_default_secret_type():
    """Test SecretMgrClient defaults secret type to 'raw'."""
    client = SecretMgrClient()
    import unittest.mock

    with unittest.mock.patch("ivcap_service.secret.requests.get") as mock_get:
        mock_response = unittest.mock.MagicMock()
        mock_response.json.return_value = {"secret-value": "test123"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        client.get_secret(secret_name="my_secret")
        call_args = mock_get.call_args
        assert call_args[1]["params"]["secret-type"] == "raw"


def test_secret_mgr_client_token_type_user():
    """Test SecretMgrClient uses USER token type by default."""
    client = SecretMgrClient()
    import unittest.mock

    with unittest.mock.patch("ivcap_service.secret.requests.get") as mock_get:
        mock_response = unittest.mock.MagicMock()
        mock_response.json.return_value = {"secret-value": "test123"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        client.get_secret(secret_name="my_secret", is_shared_secret=False)
        call_args = mock_get.call_args
        assert call_args[1]["params"]["token-type"] == "USER"


def test_secret_mgr_client_token_type_m2m():
    """Test SecretMgrClient uses M2M token type for shared secrets."""
    client = SecretMgrClient()
    import unittest.mock

    with unittest.mock.patch("ivcap_service.secret.requests.get") as mock_get:
        mock_response = unittest.mock.MagicMock()
        mock_response.json.return_value = {"secret-value": "test123"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        client.get_secret(secret_name="my_secret", is_shared_secret=True)
        call_args = mock_get.call_args
        assert call_args[1]["params"]["token-type"] == "M2M"


def test_secret_mgr_client_custom_secret_type():
    """Test SecretMgrClient accepts custom secret types."""
    client = SecretMgrClient()
    import unittest.mock

    with unittest.mock.patch("ivcap_service.secret.requests.get") as mock_get:
        mock_response = unittest.mock.MagicMock()
        mock_response.json.return_value = {"secret-value": "test123"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        client.get_secret(secret_name="my_secret", secret_type="  ssh-key  ")
        call_args = mock_get.call_args
        assert call_args[1]["params"]["secret-type"] == "ssh-key"


def test_secret_mgr_client_request_timeout():
    """Test SecretMgrClient uses custom timeout."""
    client = SecretMgrClient()
    import unittest.mock

    with unittest.mock.patch("ivcap_service.secret.requests.get") as mock_get:
        mock_response = unittest.mock.MagicMock()
        mock_response.json.return_value = {"secret-value": "test123"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        client.get_secret(secret_name="my_secret", timeout=30)
        call_args = mock_get.call_args
        assert call_args[1]["timeout"] == 30


def test_secret_mgr_client_empty_response():
    """Test SecretMgrClient handles empty response."""
    client = SecretMgrClient()
    import unittest.mock

    with unittest.mock.patch("ivcap_service.secret.requests.get") as mock_get:
        mock_response = unittest.mock.MagicMock()
        mock_response.content = b""
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        with pytest.raises(Exception, match="empty response"):
            client.get_secret(secret_name="my_secret")


def test_secret_mgr_client_request_error():
    """Test SecretMgrClient handles request exceptions."""
    client = SecretMgrClient()
    import unittest.mock

    with unittest.mock.patch("ivcap_service.secret.requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        with pytest.raises(Exception, match="Failed to read secret"):
            client.get_secret(secret_name="my_secret")


def test_secret_mgr_client_http_error():
    """Test SecretMgrClient handles HTTP errors."""
    client = SecretMgrClient()
    import unittest.mock

    with unittest.mock.patch("ivcap_service.secret.requests.get") as mock_get:
        mock_response = unittest.mock.MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Not Found"
        )
        mock_get.return_value = mock_response

        with pytest.raises(Exception, match="Failed to read secret"):
            client.get_secret(secret_name="nonexistent_secret")
