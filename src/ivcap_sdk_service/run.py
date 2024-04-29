#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#

import os
import sys
import time
import requests

from typing import Dict, Callable, Sequence, Dict
from argparse import ArgumentParser, ArgumentError
from collections import namedtuple
# import traceback

from .ivcap import init, get_config
from .logger import logger, sys_logger 
from .service import Service
from .config import Command, INSIDE_ARGO, INSIDE_CONTAINER

def run(args: Dict, handler: Callable[[Dict], int]) -> int:
    sys_logger.info(f"Starting service with '{args}'")
    code = handler(args, logger)
    return code

def _print_banner(service: Service):
    from .__init__ import __version__
    sdk_v = os.getenv('IVCAP_SDK_VERSION', __version__)
    #sdk_c = os.getenv('IVCAP_SDK_COMMIT', '#?')
    svc_v = os.getenv('IVCAP_SERVICE_VERSION', '?')
    svc_c = os.getenv('IVCAP_SERVICE_COMMIT', '?')
    svc_d = os.getenv('IVCAP_SERVICE_BUILD', '?')

    sys_logger.info(f"IVCAP Service '{service.name}' {svc_v}/{svc_c} (sdk {sdk_v}) built on {svc_d}.")

def register_service(service: Service, handler: Callable[[Dict], int]):
    if INSIDE_ARGO:
        # print banner immediately when inside the cluster
        _print_banner(service)

    init(None, service.append_arguments)
    cmd = get_config().SERVICE_COMMAND
    

    if cmd == Command.SERVICE_RUN:
        if not INSIDE_ARGO:
            _print_banner(service)
        wait_for_data_proxy()
        cfg = get_config()
        sys_logger.info(f"Starting order '{cfg.ORDER_ID}' for service '{service.name}' on node '{cfg.NODE_ID}'")
        try:
            code = run_service(service, cfg.SERVICE_ARGS, handler)
            sys.exit(code)
        except ArgumentError as perr:
            sys_logger.fatal(f"arg error '{perr}'")
        except Exception as err:
            sys_logger.exception(err)
            # sys_logger.error(f"Unexpected {err}, {type(err)}")
            # sys_logger.debug(traceback.format_exc())
            sys.exit(-1)
    elif cmd == Command.SERVICE_FILE:
        print(service.to_yaml())
    elif cmd == Command.SERVICE_HELP:
        ap = ArgumentParser(description=service.description, add_help=False)
        service.append_arguments(ap)
        ap.print_help()
    else:
        sys_logger.error(f"Unexpected command '{cmd}'")


def wait_for_data_proxy():
    if not INSIDE_ARGO:
        return

    url = f"{get_config().STORAGE_URL}/readyz"
    retries = int(os.getenv('IVCAP_DATA_PROXY_RETRIES', 5))
    delay = int(os.getenv('IVCAP_DATA_PROXY_DELAY', 3))

    for _ in range(retries):
        sys_logger.info(f"Checking for data-proxy at '{url}'.")
        try:
            requests.head(url)
            return
        except Exception:
            sys_logger.info(f"Data-proxy doesn't seem to be ready yet, will wait {delay}sec and try again.")
            time.sleep(delay)
    raise Exception(f"Can't contact data-proxy after {retries} retries on '{url}'")

def run_service(service: Service, args: Sequence[str], handler: Callable[[Dict], int]) -> int:
    ap = ArgumentParser(description=service.description)
    # Need to wait for 3.10
    # ap = ArgumentParser(description=service.description, exit_on_error=False)
    service.append_arguments(ap)
    pargs = ap.parse_args(args)
    args = vars(pargs)
    ST = namedtuple('ServiceArgs', args.keys())
    at = ST(**args)
    return run(at, handler)
    