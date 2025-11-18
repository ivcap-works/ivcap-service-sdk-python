#
# Copyright (c) 2023-2025 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
import os
from typing import Optional
import requests
from .logger import getLogger

logger = getLogger("secret")

def get_secret(secret_name:str) -> str:
    """Fetch and return the secret value from either the secret store or from an environment variable of the
    same name. Additionally, set the environment variable 'secret_name' to the secret, if not already set."""
    secret_value = os.getenv(secret_name)
    if not secret_value:
        try:
            secret_mgr_client = SecretMgrClient()
            secret_value = secret_mgr_client.get_secret(secret_name=secret_name, is_shared_secret=True)
            os.environ[secret_name] = secret_value
        except Exception as e:
            logger.error("failed to get secret '%s' - %s", secret_name, e)
            raise e
    logger.info("got secret '%s' ending in '%s'", secret_name, secret_value[-5:])
    return secret_value

class SecretMgrClient:
    """The IVCAP Secret Manager Client willread secret through http via:
- Service side car
"""
    def __init__(self,
        secret_url: Optional[str] = None
    ) -> None:
        if not secret_url:
            secret_url = os.getenv("SECRETMGR_PROXY", "http://secretmgr.local")
        self.secret_url = secret_url

    def get_secret(self, secret_name: str, is_shared_secret: bool = False, secret_type: str = "", timeout: int = 10) -> str:
        try:
            url = f"{self.secret_url}/1/secret"

            secret_name = secret_name.strip()
            if not secret_name:
                raise ValueError("empty secret name")

            secret_type = secret_type.strip()
            if not secret_type:
                secret_type = "raw"

            token_type = "USER"
            if is_shared_secret:
                token_type = "M2M"

            params = {
                "secret-name": secret_name,
                "secret-type": secret_type,
                "token-type":  token_type,
            }

            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()

            if not response.content:
                raise Exception("Failed to read secret: empty response received.")

            data = response.json()
            return data["secret-value"]
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to read secret: {e}")