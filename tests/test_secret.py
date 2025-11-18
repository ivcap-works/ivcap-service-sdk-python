#
# Copyright (c) 2025 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
import os

from ivcap_service import get_secret


def test_secret_from_env():
    os.environ["MY_TEST_SECRET"] = "supersecretvalue"
    secret = get_secret("MY_TEST_SECRET")
    assert secret == "supersecretvalue"