#
# Copyright (c) 2025 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#

import time
import traceback
from typing import Callable, Tuple
import argparse
from logging import Logger
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlunparse

import os
import sys
import httpx
from pydantic import BaseModel, ConfigDict, Field
import requests

from .context import JobContext, otel_instrument, set_context
from .ivcap import get_ivcap_url, push_result, verify_result
from .logger import getLogger
from .types import ExecutionError
from .utils import get_function_return_type, get_input_type
from .version import get_version
from .tool_definition import print_tool_definition  # Import the requests library
from .events import EventReporter

class ServiceContact(BaseModel):
    name: str = Field(description="name of the contact person")
    email: str = Field(description="email address of the contact person")
    url: Optional[str] = Field(None, description="url of the contact person")

class ServiceLicense(BaseModel):
    name: str = Field(description="name of the license")
    url: str = Field(description="url to the license text")

class Service(BaseModel):
    name: str = Field(description="name of the service")
    version: Optional[str] = Field(os.environ.get("VERSION", "???"), description="version of the service")
    contact: ServiceContact = Field(description="contact details of the service")
    license: Optional[ServiceLicense] = Field(None, description="license of the service")

# Number of attempt to request a new job before giving up
MAX_REQUEST_JOB_ATTEMPTS = 4

class ServiceContext(BaseModel):
    worker_fn: Callable
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    fn_add_job_context: Optional[str]
    job_context: Optional[JobContext] = None
    logger: Logger

    model_config = ConfigDict(arbitrary_types_allowed=True)

def wait_for_work(svc_ctxt: ServiceContext):
    ivcap_url = get_ivcap_url()
    if ivcap_url is None:
        svc_ctxt.logger.warning(f"no ivcap url found - cannot request work")
        return
    url = urlunparse(ivcap_url._replace(path=f"/next_job"))
    logger = svc_ctxt.logger
    logger.info(f"... checking for work at '{url}'")
    try:

        while True:
            result = None
            try:
                (response, job_authorization) = fetch_job(url, logger)
                job = response.json()
                schema = job.get("$schema", "")
                if schema.startswith("urn:ivcap:schema.service.batch.done"):
                    logger.info("no more jobs - we are done")
                    sys.exit(0)

                job_id = job.get("id", "unknown_job_id")  # Provide a default value if "id" is missing
                result = do_job(job, svc_ctxt, job_authorization)
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
                    push_result(result, job_id, None)

    except requests.exceptions.RequestException as e:
        logger.warning(f"Error during request: {e}")
    except Exception as e:
        logger.warning(f"Error processing job: {e}")

def fetch_job(url: str, logger: Logger) -> Tuple[Any, Optional[str]]:
    wait_time = 1
    attempt = 0
    while attempt < MAX_REQUEST_JOB_ATTEMPTS:
        try:
            response = httpx.get(url)
            response.raise_for_status()
            job_authorization = response.headers.get("authorization")
            return (response, job_authorization)
        except Exception as e:
            attempt += 1
            logger.info(f"attempt #{attempt} failed to fetch new job - will try again in {wait_time} sec - {type(e)}: {e}")
            time.sleep(wait_time)
            wait_time *= 2
    logger.info("cannot contact sidecar - bailing out")
    sys.exit(255)

def do_job(
    job: Any,
    svc_ctxt: ServiceContext,
    job_authorization: Optional[str] = None
):
    job_id = job.get("id", "unknown_job_id")  # Provide a default value if "id" is missing
    ct = job["in-content-type"]
    if ct != "application/json":
        raise Exception(f"cannot handle content-type '{ct}'")
    jc = job["in-content"]
    logger = svc_ctxt.logger
    mreq = svc_ctxt.input_model(**jc)
    logger.info(f"{job_id}: calling worker with - {mreq}")
    svc_ctxt.job_context = JobContext(job_id=job_id, job_authorization=job_authorization, report=EventReporter(job_id=job_id))
    try:
        f = svc_ctxt.worker_fn
        if svc_ctxt.fn_add_job_context is None:
            resp = f(mreq)
        else:
            d = {}
            d[svc_ctxt.fn_add_job_context] = svc_ctxt.job_context
            resp = f(mreq, **d)
        logger.info(f"{job_id}: worker finished with - {resp}")
        if type(resp) != svc_ctxt.output_model:
            logger.warning(f"{job_id}: result is of type '{type(resp)}' but expected '{svc_ctxt.output_model}'")

    except BaseException as ex:
        logger.warning(f"{job_id}: failed - '{ex}'")
        resp = ExecutionError(
                        error=str(ex),
                        type=type(ex).__name__,
                        traceback=traceback.format_exc()
                    )
    return resp

def start_batch_service(
    service_description: Service,
    worker_fn: Callable,
    *,
    custom_args: Optional[Callable[[argparse.ArgumentParser], argparse.Namespace]] = None,
    run_opts: Optional[Dict[str, Any]] = None,
    with_telemetry: Optional[bool] = None,
):
    """A helper function to start a batch service

    Args:
        service_description (Service): description of the service
        tool_fn (Callable[..., Any]): _description_
        logger (Logger): _description_
        custom_args (Optional[Callable[[argparse.ArgumentParser], argparse.Namespace]], optional): _description_. Defaults to None.
        run_opts (Optional[Dict[str, Any]], optional): _description_. Defaults to None.
        with_telemetry: (Optional[bool]): Instantiate or block use of OpenTelemetry tracing
    """
    logger = getLogger("server")

    parser = argparse.ArgumentParser(description=service_description.name)
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
        print_batch_service_definition(service_description, worker_fn)
        sys.exit(0)

    if args.print_tool_description:
        print_tool_definition(worker_fn, name = service_description.name)
        sys.exit(0)

    logger.info(f"{service_description.name} - {os.getenv('VERSION')} - v{get_version()}")

    svc_ctxt = create_service_context(worker_fn, logger)
    if args.test_file is not None:
        from .utils import file_to_json
        job = file_to_json(args.test_file)
        resp = do_job(job, svc_ctxt)

        # res = verify_result(resp, "0000-000", logger)
        # push_result(res, "0000-000", None)

        print(resp.model_dump_json(indent=2, by_alias=True))
    else:
        otel_instrument(with_telemetry, None, logger)
        set_context(lambda: svc_ctxt.job_context)
        wait_for_work(svc_ctxt)


def create_service_context(worker_fn: Callable, logger: Logger) -> ServiceContext:
    input_model, extras = get_input_type(worker_fn)
    if len(extras) > 1:
        logger.warning(f"worker function '{worker_fn.__name__}' has more than one extra paramter - only JobContext is allowed")
        sys.exit(1)
    fn_job_context_p = None
    if len(extras) == 1:
        fn_job_context_p = list(extras.keys())[0]
        if extras[fn_job_context_p] != JobContext:
            logger.warning(f"worker function '{worker_fn.__name__}' can only have 'JobContext' as additional parameter")
            sys.exit(1)

    output_model = get_function_return_type(worker_fn)

    return ServiceContext(
        worker_fn=worker_fn,
        fn_add_job_context=fn_job_context_p,
        input_model=input_model,
        output_model=output_model,
        logger=logger,
    )
