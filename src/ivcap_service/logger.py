#
# Copyright (c) 2025 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
import json
import logging
from logging.config import dictConfig
import os

LOGGING_CONFIG={}

def getLogger(name: str) -> logging.Logger:
    return logging.getLogger(name)

def service_log_config():
    return LOGGING_CONFIG

def logging_init(cfg_path: str=None):
    if not cfg_path:
        script_dir = os.path.dirname(__file__)
        cfg_path = os.path.join(script_dir, "logging.json")

    with open(cfg_path, 'r') as file:
        global LOGGING_CONFIG
        LOGGING_CONFIG = json.load(file)
        dictConfig(LOGGING_CONFIG)