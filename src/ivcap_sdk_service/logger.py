#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#

import logging as _logging
import sys

# format
DEF_LEVEL = _logging.DEBUG
_format = '%(levelname)s %(asctime)s %(name)s %(message)s'
_datefmt = '%Y-%m-%dT%H:%M:%S%z'

_formatter = _logging.Formatter(_format, _datefmt)
_console = _logging.StreamHandler(sys.stdout)
_console.setFormatter(_formatter)
_console.setLevel(_logging.DEBUG)
_logging.propagate = False
_logging.root.handlers = []

logger = _logging.getLogger("service")
logger.setLevel(DEF_LEVEL)
logger.addHandler(_console)
logger.propagate = False

sys_logger = _logging.getLogger("ivcap")
sys_logger.setLevel(DEF_LEVEL)
sys_logger.addHandler(_console)
logger.propagate = False
