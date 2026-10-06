import os
import sys

this_dir = os.path.dirname(__file__)
src_dir = os.path.abspath(os.path.join(this_dir, "../.."))
sys.path.insert(0, src_dir)

from ivcap_service import (  # noqa: E402
    Service,
    ServiceContact,
    ServiceLicense,
    getLogger,
    logging_init,
)
from ivcap_service.testkit import process_job  # noqa: E402

logging_init()
logger = getLogger("app")

service = Service(
    name="Batch service example",
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


if __name__ == "__main__":
    from ivcap_service import start_batch_service

    start_batch_service(service, process_job)
