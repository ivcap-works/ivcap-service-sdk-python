import os

import httpx
from pydantic import BaseModel, Field

from ivcap_service import JobContext, getLogger, logging_init, with_schema
from ivcap_service.service import Service, ServiceContact, ServiceLicense

logging_init()
logger = getLogger("app")

service = Service(
    name="Batch API Tester",
    version=os.environ.get("VERSION", "???"),
    contact=ServiceContact(
        name="Mary Doe",
        email="mary.doe@acme.au",
    ),
    license=ServiceLicense(
        name="MIT",
        url="https://opensource.org/license/MIT",
    ),
)


@with_schema("urn:sd:schema:batch-tester.request.1")
class Request(BaseModel):
    get: str | None = Field(
        None, description="perform a GET on this url and return result"
    )
    artifact: str | None = Field(
        None, description="download artifact 'as_local_file' and return local path"
    )


@with_schema("urn:sd:schema:batch-tester.1")
class Result(BaseModel):
    result: str | None = Field(None, description="serialised result")


def api_tester(req: Request, ctxt: JobContext) -> Result:
    """
    Run some API tests from inside a batch process
    """
    if req.get:
        with ctxt.report.step("get", msg="Run 'GET' command"):
            response = httpx.get(req.get)
            response.raise_for_status()
            logger.info(f"Status Code: {response.status_code}")
            return Result(result=response.text)

    if req.artifact:
        art = ctxt.ivcap.get_artifact(req.artifact)
        path = art.as_local_file()  # type: ignore[attr-defined]
        return Result(result=str(path))
    else:
        raise ValueError("Missing command")


if __name__ == "__main__":
    from ivcap_service import start_batch_service

    start_batch_service(service, api_tester)
