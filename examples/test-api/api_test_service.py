import os
from typing import Optional
import httpx
from pydantic import BaseModel, Field
from ivcap_service import getLogger, logging_init, JobContext
from ivcap_service.service import Service

logging_init()
logger = getLogger("app")

service = Service(
    name="Batch API Tester",
    version=os.environ.get("VERSION", "???"),
    contact={
        "name": "Mary Doe",
        "email": "mary.doe@acme.au",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/license/MIT",
    },
)

class Request(BaseModel):
    jschema: str = Field("urn:sd:schema:batch-tester.request.1", alias="$schema")
    get: Optional[str] = Field(None, description="perform a GET on this url and return result")
    artifact: Optional[str] = Field(None, description="download artifact 'as_local_file' and return local path")

class Result(BaseModel):
    jschema: str = Field("urn:sd:schema:batch-tester.1", alias="$schema")
    result: str = Field(None, description="serialised result")

def api_tester(req: Request, ctxt: JobContext) -> Result:
    """
    Run some API tests from inside a batch process
    """
    if req.get:
        with ctxt.report.step("get", msg=f"Run 'GET' command"):
            response = httpx.get(req.get)
            response.raise_for_status()
            logger.info(f"Status Code: {response.status_code}")
            return Result(result=response.text)

    if req.artifact:
        art = ctxt.ivcap.get_artifact(req.artifact)
        return art.as_local_file()
    else:
        raise "Missing command"

if __name__ == "__main__":
    from ivcap_service import start_batch_service
    start_batch_service(service, api_tester)
