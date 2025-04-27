#
# Copyright (c) 2025 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#

import time
import traceback
from typing import Callable
import argparse
from logging import Logger
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlunparse

import os
import sys
from pydantic import BaseModel
import requests


from .ivcap import get_ivcap_url, push_result, verify_result
from .logger import getLogger
from .types import ExecutionError
from .utils import _get_function_return_type, _get_input_type, get_version
from .tool_definition import print_tool_definition  # Import the requests library

# Number of attempt to request a new job before giving up
MAX_REQUEST_JOB_ATTEMPTS = 4

def wait_for_work(worker_fn: Callable, input_model: type[BaseModel], output_model: type[BaseModel], logger: Logger):
    ivcap_url = get_ivcap_url()
    if ivcap_url is None:
        logger.warning(f"no ivcap url found - cannot request work")
        return
    url = urlunparse(ivcap_url._replace(path=f"/next_job"))
    logger.info(f"... checking for work at '{url}'")
    try:

        while True:
            result = None
            try:
                response = fetch_job(url, logger)
                job = response.json()
                schema = job.get("$schema", "")
                if schema.startswith("urn:ivcap:schema.service.batch.done"):
                    logger.info("no more jobs - we are done")
                    sys.exit(0)

                job_id = job.get("id", "unknown_job_id")  # Provide a default value if "id" is missing
                result = do_job(job, worker_fn, input_model, output_model, logger)
                result = verify_result(result, job_id, logger)
            except Exception as e:
                result = ExecutionError(
                    error=str(e),
                    type=type(e).__name__,
                    traceback=traceback.format_exc()
                )
                logger.warning(f"job {job_id} failed - {result.error}")
            finally:
                if result is not None:
                    logger.info(f"job {job_id} finished, sending result message")
                    push_result(result, job_id, None, logger)

    except requests.exceptions.RequestException as e:
        logger.warning(f"Error during request: {e}")
    except Exception as e:
        logger.warning(f"Error processing job: {e}")

def fetch_job(url: str, logger: Logger) -> Any:
    wait_time = 1
    attempt = 0
    while attempt < MAX_REQUEST_JOB_ATTEMPTS:
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response
        except Exception as e:
            attempt += 1
            logger.info(f"attempt #{attempt} failed to fetch new job - will try again in {wait_time} sec - {type(e)}: {e}")
            time.sleep(wait_time)
            wait_time *= 2
    logger.info("cannot contact sidecar - bailing out")
    sys.exit(255)

def do_job(
    job: Any,
    worker_fn: Callable,
    input_model: type[BaseModel],
    output_model: type[BaseModel],
    logger: Logger
):
    job_id = job.get("id", "unknown_job_id")  # Provide a default value if "id" is missing
    ct = job["in-content-type"]
    if ct != "application/json":
        raise Exception(f"cannot handle content-type '{ct}'")
    jc = job["in-content"]
    mreq = input_model(**jc)
    logger.info(f"{job_id}: calling worker with - {mreq}")
    try:
        resp = worker_fn(mreq)
        logger.info(f"{job_id}: worker finished with - {resp}")
        if type(resp) != output_model:
            logger.warning(f"{job_id}: result is of type '{type(resp)}' but expected '{output_model}'")

    except BaseException as ex:
        logger.warning(f"{job_id}: failed - '{ex}'")
        resp = ExecutionError(
                        error=str(ex),
                        type=type(ex).__name__,
                        traceback=traceback.format_exc()
                    )
    return resp

def start_batch_service(
    title: str,
    worker_fn: Callable,
    *,
    custom_args: Optional[Callable[[argparse.ArgumentParser], argparse.Namespace]] = None,
    run_opts: Optional[Dict[str, Any]] = None,
    with_telemetry: Optional[bool] = None,
):
    """A helper function to start a batch service

    Args:
        title (str): the tile
        tool_fn (Callable[..., Any]): _description_
        logger (Logger): _description_
        custom_args (Optional[Callable[[argparse.ArgumentParser], argparse.Namespace]], optional): _description_. Defaults to None.
        run_opts (Optional[Dict[str, Any]], optional): _description_. Defaults to None.
        with_telemetry: (Optional[bool]): Instantiate or block use of OpenTelemetry tracing
    """
    logger = getLogger("server")

    parser = argparse.ArgumentParser(description=title)
    parser.add_argument('--with-telemetry', action="store_true", help='Initialise OpenTelemetry')
    parser.add_argument('--print-service-description', action="store_true", help='Print service description to stdout')
    parser.add_argument('--print-tool-description', action="store_true", help='Print tool description to stdout')
    parser.add_argument('--test-file', type=str, help='path to job file for testing service')

    if custom_args is not None:
        args = custom_args(parser)
    else:
        args = parser.parse_args()

    if args.print_service_description:
        from .service_definition import print_batch_service_definition
        print_batch_service_definition(worker_fn)
        sys.exit(0)

    if args.print_tool_description:
        print_tool_definition(worker_fn)
        sys.exit(0)

    logger.info(f"{title} - {os.getenv('VERSION')} - v{get_version()}")

    input_model, _ = _get_input_type(worker_fn)
    output_model = _get_function_return_type(worker_fn)
    # summary, description = (worker_fn.__doc__.lstrip() + "\n").split("\n", 1)

    if args.test_file is not None:
        from .utils import file_to_json
        job = file_to_json(args.test_file)
        resp = do_job(job, worker_fn, input_model, output_model, logger)
        print(resp.model_dump_json(indent=2, by_alias=True))
    else:
        wait_for_work(worker_fn, input_model, output_model, logger)
